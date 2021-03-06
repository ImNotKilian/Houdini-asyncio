from houdini import handlers
from houdini.handlers import XTPacket

from houdini.data import db
from houdini.data.penguin import Penguin
from houdini.data.buddy import IgnoreList
from houdini.data.mail import PenguinPostcard

import time
import random
import datetime


@handlers.handler(XTPacket('l', 'mst'))
@handlers.allow_once
async def handle_start_mail_engine(p):
    postcards = []
    if not p.data.agent_status and random.random() < 0.4:
        epf_invited = await PenguinPostcard.query.where(
            (PenguinPostcard.penguin_id == p.data.id) & ((PenguinPostcard.postcard_id == 112)
                                                         | (PenguinPostcard.postcard_id == 47))).gino.scalar()
        if not epf_invited:
            postcards.append({
                'penguin_id': p.data.id,
                'postcard_id': 112
            })

    last_paycheck = p.data.last_paycheck.date()
    today = datetime.date.today()
    first_day_of_month = today.replace(day=1)
    last_paycheck = last_paycheck.replace(day=1)

    player_data = p.data
    while last_paycheck < first_day_of_month:
        last_paycheck = last_paycheck + datetime.timedelta(days=32)
        last_paycheck = last_paycheck.replace(day=1)
        send_date = last_paycheck + datetime.timedelta(days=1)
        if 428 in p.data.inventory:
            postcards.append({
                'penguin_id': p.data.id,
                'postcard_id': 172,
                'send_date': send_date
            })
            player_data.update(coins=p.data.coins + 250)
        if p.data.agent_status:
            postcards.append({
                'penguin_id': p.data.id,
                'postcard_id': 184,
                'send_date': send_date
            })
            player_data.update(coins=p.data.coins + 350)

    await player_data.update(last_paycheck=last_paycheck).apply()
    if postcards:
        await PenguinPostcard.insert().values(postcards).gino.status()

    mail_count = await db.select([db.func.count(PenguinPostcard.id)]).where(
        PenguinPostcard.penguin_id == p.data.id).gino.scalar()
    unread_mail_count = await db.select([db.func.count(PenguinPostcard.id)]).where(
        (PenguinPostcard.penguin_id == p.data.id)
        & (PenguinPostcard.has_read == False)).gino.scalar()
    await p.send_xt('mst', unread_mail_count, mail_count)


@handlers.handler(XTPacket('l', 'mg'))
@handlers.allow_once
async def handle_get_mail(p):
    mail_query = PenguinPostcard.load(parent=Penguin.on(Penguin.id == PenguinPostcard.sender_id)).where(
        PenguinPostcard.penguin_id == p.data.id).order_by(
        PenguinPostcard.send_date.desc())

    postcards = []
    async with p.server.db.transaction():
        async for postcard in mail_query.gino.iterate():
            sender_name, sender_id = ('sys', 0) if postcard.sender_id is None else (
                postcard.parent.nickname, postcard.sender_id)
            sent_timestamp = int(time.mktime(postcard.send_date.timetuple()))
            postcards.append(f'{sender_name}|{sender_id}|{postcard.postcard_id}|'
                             f'{postcard.details}|{sent_timestamp}|{postcard.id}|{int(postcard.has_read)}')
    await p.send_xt('mg', *postcards)


@handlers.handler(XTPacket('l', 'ms'))
@handlers.cooldown(2)
async def handle_send_mail(p, recipient_id: int, postcard_id: int):
    if p.data.coins < 10:
        return await p.send_xt('ms', p.data.coins, 0)
    if recipient_id in p.server.penguins_by_id:
        recipient = p.server.penguins_by_id[recipient_id]
        if p.data.id in recipient.data.ignore:
            return await p.send_xt('ms', p.data.coins, 1)
        if len(recipient.data.postcards) >= 100:
            return await p.send_xt('ms', p.data.coins, 0)
        postcard = await PenguinPostcard.create(penguin_id=recipient_id, sender_id=p.data.id,
                                                postcard_id=postcard_id)
        sent_timestamp = int(time.mktime(postcard.send_date.timetuple()))
        await recipient.send_xt('mr', p.data.nickname, p.data.id, postcard_id, '', sent_timestamp, postcard.id)
    else:
        ignored = await IgnoreList.query.where((IgnoreList.penguin_id == recipient_id)
                                               & (IgnoreList.ignore_id == p.data.id)).gino.scalar()
        if ignored is not None:
            return await p.send_xt('ms', p.data.coins, 1)
        mail_count = await db.select([db.func.count(PenguinPostcard.id)]).where(
            PenguinPostcard.penguin_id == recipient_id).gino.scalar()
        if mail_count >= 100:
            return await p.send_xt('ms', p.data.coins, 0)
        await PenguinPostcard.create(penguin_id=recipient_id, sender_id=p.data.id, postcard_id=postcard_id)
    await p.data.update(coins=p.data.coins - 10).apply()
    return await p.send_xt('ms', p.data.coins, 1)


@handlers.handler(XTPacket('l', 'mc'))
async def handle_mail_checked(p):
    await PenguinPostcard.update.values(has_read=True).where(
        PenguinPostcard.penguin_id == p.data.id).gino.status()


@handlers.handler(XTPacket('l', 'md'))
async def handle_delete_mail(p, postcard_id: int):
    await PenguinPostcard.delete.where((PenguinPostcard.penguin_id == p.data.id)
                                       & (PenguinPostcard.id == postcard_id)).gino.status()


@handlers.handler(XTPacket('l', 'mdp'))
async def handle_delete_mail_from_user(p, sender_id: int):
    sender_id = None if sender_id == 0 else sender_id
    await PenguinPostcard.delete.where((PenguinPostcard.penguin_id == p.data.id)
                                       & (PenguinPostcard.sender_id == sender_id)).gino.status()
    mail_count = await db.select([db.func.count(PenguinPostcard.id)]).where(
        PenguinPostcard.penguin_id == p.data.id).gino.scalar()
    await p.send_xt('mdp', mail_count)
