from houdini import handlers
from houdini.handlers import XTPacket
from houdini.data.item import Item, ItemCrumbsCollection

import time
from aiocache import cached
import operator


def get_pin_string_key(_, p, player_id):
    return 'pins.{}'.format(player_id)


def get_awards_string_key(_, p, player_id):
    return 'awards.{}'.format(player_id)


@cached(alias='default', key_builder=get_pin_string_key)
async def get_pin_string(p, player_id):
    if player_id in p.server.penguins_by_id:
        inventory = p.server.penguins_by_id[player_id].data.inventory
    else:
        inventory = await ItemCrumbsCollection.get_collection(player_id)

    def get_string(pin):
        unix = int(time.mktime(pin.release_date.timetuple()))
        return f'{pin.id}|{unix}|{int(pin.member)}'

    pins = sorted((p.server.items[pin] for pin in inventory.keys()
                   if (p.server.items[pin].is_flag() and p.server.items[pin].cost == 0)),
                  key=operator.attrgetter('release_date'))
    return '%'.join(get_string(pin) for pin in pins)


@cached(alias='default', key_builder=get_awards_string_key)
async def get_awards_string(p, player_id):
    if player_id in p.server.penguins_by_id:
        inventory = p.server.penguins_by_id[player_id].data.inventory
    else:
        inventory = await ItemCrumbsCollection.get_collection(player_id)

    awards = [str(award) for award in inventory.keys() if p.server.items[award].is_award()]
    return '%'.join(awards)


@handlers.handler(XTPacket('i', 'gi'))
@handlers.allow_once
async def handle_get_inventory(p):
    await p.send_xt('gi', *p.data.inventory.keys())


@handlers.handler(XTPacket('i', 'ai'))
@handlers.depends_on_packet(XTPacket('i', 'gi'))
async def handle_buy_inventory(p, item: Item):
    if item.id not in p.server.items:
        return await p.send_error(402)

    if item.id in p.data.inventory:
        return await p.send_error(400)

    if item.tour:
        return await p.add_inbox(p.server.postcards[126])

    if p.data.coins < item.cost:
        return await p.send_error(401)

    await p.add_inventory(item)


@handlers.handler(XTPacket('i', 'qpp'))
@handlers.depends_on_packet(XTPacket('i', 'gi'))
@handlers.cooldown(1)
async def handle_query_player_pins(p, player_id: int):
    await p.send_xt('qpp', await get_pin_string(p, player_id))


@handlers.handler(XTPacket('i', 'qpa'))
@handlers.depends_on_packet(XTPacket('i', 'gi'))
@handlers.cooldown(1)
async def handle_query_player_awards(p, player_id: int):
    await p.send_xt('qpa', await get_awards_string(p, player_id))
