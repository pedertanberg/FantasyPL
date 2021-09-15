
from update_team import update
import asyncio
import aiohttp
import os
import datetime
import pandas as pd
from fpl import FPL
import time

EMAIL = "XXXXX"
PASSWORD = "XXXX"
USER_ID = XXXX

def days_hours_minutes(td):
    return td.days, td.seconds//3600, (td.seconds//60)%60


async def check_update():
    async with aiohttp.ClientSession() as session:
        fpl = FPL(session)
        gw = await fpl.get_gameweeks(return_json=True)
        df = pd.DataFrame(gw)
        today = datetime.datetime.now()
        print(today)
        today_timestamp = today.timestamp()
        df = df.loc[df.deadline_time_epoch>today_timestamp]
        deadline = df.iloc[0].deadline_time_epoch
        print("Deadline",deadline)
        tomorrow=float(datetime.timedelta(days=1).total_seconds())
        print("Test", datetime.timedelta(days=1).total_seconds())  
        unixtimeToday = today.timestamp()
        print(unixtimeToday+tomorrow)
        return deadline<unixtimeToday + tomorrow


if __name__ == "__main__":
    if asyncio.run(check_update()):
        email=EMAIL
        password=PASSWORD
        user_id=USER_ID
        asyncio.run(update(email, password,user_id))