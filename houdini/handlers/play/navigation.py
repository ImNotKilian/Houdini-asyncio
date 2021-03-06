from houdini import handlers
from houdini.handlers import XTPacket
from houdini.data.room import Room
from houdini.data.penguin import Login

import random
import time
from datetime import datetime


@handlers.handler(XTPacket('j', 'js'), pre_login=True)
@handlers.allow_once
async def handle_join_server(p, penguin_id: int, login_key: str):
    if penguin_id != p.data.id:
        return await p.close()

    if login_key != p.login_key:
        return await p.close()

    await p.send_xt('activefeatures')

    moderator_status = 3 if p.data.character else 2 if p.data.stealth_moderator else 1 if p.data.moderator else 0

    await p.send_xt('js', int(p.data.agent_status), int(0),
                    moderator_status, int(p.data.book_modified))

    current_time = int(time.time())
    penguin_standard_time = current_time * 1000
    server_time_offset = 7

    if p.data.timer_active:
        minutes_until_timer_end = datetime.combine(datetime.today(), p.data.timer_end) - datetime.now()
        minutes_until_timer_end = minutes_until_timer_end.total_seconds() // 60

        minutes_played_today = await p.data.minutes_played_today
        minutes_left_today = (p.data.timer_total.total_seconds() // 60) - minutes_played_today
        p.egg_timer_minutes = int(min(minutes_until_timer_end, minutes_left_today))
    else:
        p.egg_timer_minutes = 24 * 60

    await p.send_xt('lp', await p.string, p.data.coins, int(p.data.safe_chat), p.egg_timer_minutes,
                    penguin_standard_time, p.data.age, 0, p.data.minutes_played,
                    "membership_days", server_time_offset, int(p.data.opened_playercard),
                    p.data.map_category, p.data.status_field)

    spawn = random.choice(p.server.spawn_rooms)
    await p.join_room(spawn)

    await p.data.load_inventories()

    p.server.penguins_by_id[p.data.id] = p
    p.server.penguins_by_username[p.data.username] = p

    if p.data.character is not None:
        p.server.penguins_by_character_id[p.data.character] = p

    p.login_timestamp = datetime.now()
    p.joined_world = True

    server_key = '{}.players'.format(p.server.server_config['Id'])
    await p.server.redis.sadd(server_key, p.data.id)
    await p.server.redis.hincrby('population', p.server.server_config['Id'], 1)


@handlers.handler(XTPacket('j', 'jr'))
@handlers.cooldown(1)
async def handle_join_room(p, room: Room, x: int, y: int):
    p.x, p.y = x, y
    await p.join_room(room)


@handlers.handler(XTPacket('j', 'grs'))
async def handle_refresh_room(p):
    await p.room.refresh(p)


@handlers.disconnected
@handlers.player_attribute(joined_world=True)
async def handle_disconnect_room(p):
    await p.room.remove_penguin(p)

    minutes_played = (datetime.now() - p.login_timestamp).total_seconds() / 60.0
    await Login.create(penguin_id=p.data.id,
                       date=p.login_timestamp,
                       ip_address=p.peer_name[0],
                       minutes_played=minutes_played)

    await p.data.update(minutes_played=p.data.minutes_played + minutes_played).apply()

    del p.server.penguins_by_id[p.data.id]
    del p.server.penguins_by_username[p.data.username]

    server_key = '{}.players'.format(p.server.server_config['Id'])
    await p.server.redis.srem(server_key, p.data.id)
    await p.server.redis.hincrby('population', p.server.server_config['Id'], -1)
