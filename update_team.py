from os import error
from fpl import FPL
import aiohttp
import asyncio
from numpy.lib.ufunclike import fix
import pandas as pd
from datetime import datetime

async def update(email, password,user_id):
  async with aiohttp.ClientSession() as session:
    fpl = FPL(session)
    login = await fpl.login(email, password)
    user = await fpl.get_user(user_id)

    gw = await fpl.get_gameweeks(return_json=True)
    df = pd.DataFrame(gw)
    print(df)
    today = datetime.now().timestamp()
    df = df.loc[df.deadline_time_epoch>today]
    gameweek= df.iloc[0].id
    picks = await user.get_picks(gameweek-1)
    print(picks)


    players = [x['element'] for x in picks[gameweek-1]]
    picked_players = []
    for player in players:
        p = await fpl.get_player(player, return_json=True)
        picked_players.append(p.copy())
    picked_players = pd.DataFrame(picked_players)

    print(picked_players)
    print(picked_players['web_name'])
    picked_players["chance_of_playing_this_round"]= picked_players["chance_of_playing_this_round"].fillna(100)
    print(picked_players)


    fixtures = await fpl.get_fixtures_by_gameweek(gameweek, return_json=True)
    fixtures = pd.DataFrame(fixtures)
    print(fixtures)

    test = calc_fdr_diff(picked_players,fixtures)
    print("TEST 1 BITCH",test)

    player_out=calc_player_out(test,fixtures)
    print("over here",player_out)

    check = await user.get_transfers_status()
    print(check['bank'])
    check1 = check['bank']
    last_deadline_bank = check1/10
    print(last_deadline_bank)
    player_out_cost =int(player_out[1]['now_cost'])
    real_player_out_cost = player_out_cost/10
    budget =last_deadline_bank+real_player_out_cost
    print("budget", budget)
    dups_team = picked_players.pivot_table(index=['team'], aggfunc='size')
    invalid_teams = dups_team.loc[dups_team==3].index.tolist()

    potential_players = await fpl.get_players()
    player_dict = [dict(vars(x)) for x in potential_players]
    df=  pd.DataFrame(player_dict)
    df = df[~df['team'].isin(invalid_teams)]
    print("is in team",df['now_cost'])
    df = df[(df['now_cost']<budget*10)]
    print("budget",df)
    df= df.loc[~df['id'].isin(picked_players['id'].tolist())]
    print("iloc",player_out[1])
    player_out_pd =player_out[1] 
    print("MIO",player_out_pd)
    element_type = int(player_out_pd['element_type'].iloc[0])
    print(element_type)
    print(df)
    df = df.loc[df['element_type']==element_type]
    print(df)
    df["chance_of_playing_this_round"]= df["chance_of_playing_this_round"].fillna(100)

    picked_players.index = range(15)
    rows_to_drop=player_out_pd.index.values.astype(int)[0]
    picked_players=picked_players.drop(rows_to_drop)
    df = calc_fdr_diff(df, fixtures)
    print(df)
    print("DONE")
    player_in_df = calc_player_in(df,fixtures)
    player_in = [int(player_in_df['id'].iloc[0])]
    player_out1 = [int(player_out_pd['id'].iloc[0])]
    print("This is the MF going out",player_out_pd['web_name'].iloc[0],"-",player_out_pd['first_name'].iloc[0],"-",player_out_pd['id'].iloc[0],"-",player_out_pd['now_cost'].iloc[0])
    print("This mf is coming in",player_in_df['web_name'].iloc[0]+"-",player_in_df['first_name'].iloc[0],"-",player_in_df['id'].iloc[0],"-",player_in_df['now_cost'].iloc[0] )
    print("player out", player_out1, "player in ", player_in)
    try:
        print("Starting")
        await user.transfer(player_out, player_in)
        print("success")
    except Exception as inst:
        print(type(inst))
        print(inst.args)    
        print(inst)          
        x, y = inst.args
        print('x =', x)
        print('y =', y)

    captainList=player_out[0].sort_values(by=['weight'])
    captain = captainList.iloc[0]['id']
    print("my captain",captainList.iloc[0]['first_name'])



def calc_fdr_diff(players, fixes):
    fixes = fixes[['team_a', "team_h", "team_h_difficulty", "team_a_difficulty"]]    
    away_df = pd.merge(players, fixes, how="inner", left_on=["team"], right_on=["team_a"])    
    home_df = pd.merge(players, fixes, how="inner", left_on=["team"], right_on=["team_h"])   
    print(away_df) 
    away_df['fdr'] = away_df['team_a_difficulty']-home_df['team_h_difficulty']-1    
    home_df['fdr'] = home_df['team_h_difficulty']-home_df['team_a_difficulty']+1    
    df = away_df.append(home_df)
    df.index = range(len(df))
    return df

def calc_player_out(players, fixtures):
    teams_playing = fixtures[["team_a", "team_h"]].values.ravel()
    teams_playing = pd.unique(teams_playing)
    ps_not_playing = players.loc[~players.team.isin(teams_playing)]
    teams_playing_twice = [x for x in teams_playing if list(teams_playing).count(x)>1]
    ps_playing_twice=players.loc[players.team.isin(teams_playing_twice)]
    df1 = pd.DataFrame(columns=players.columns.tolist())
    for x in players.iterrows():
        weight = 25
        weight-= x[1]['fdr']*3
        print(weight)
        weight-= float(x[1]['form'])*4
        weight += (100-float(x[1]['chance_of_playing_this_round']))*0.2
        if x[1]['id'] in ps_not_playing['id']:
            weight+=25
        if x[1]['id'] in ps_playing_twice['id']:
            weight -=25
        if weight < 0:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])
    print(df1['web_name'])
    return df1,df1.sample(1, weights=df1['weight'])


def calc_player_in(df, fixtures):    
    df1 = pd.DataFrame(columns=df.columns.tolist())
    teams_playing = fixtures[["team_a", "team_h"]].values.ravel()
    teams_playing = pd.unique(teams_playing)    
    teams_playing_twice = [x for x in teams_playing if list(teams_playing).count(x)>1]    
    ps_not_playing = df.loc[~df.team.isin(teams_playing)]
    ps_playing_twice=df.loc[df.team.isin(teams_playing_twice)]
    for x in df.iterrows():
        weight = 0.1
        weight+= x[1]['fdr']*3
        weight+= float(x[1]['form'])*4
        weight -= (100-float(x[1]['chance_of_playing_this_round'])) * 0.2        
        if weight < 0:
            weight = 0
        if x[1]['id'] in ps_not_playing['id']:
            weight+=5
        if x[1]['id'] in ps_playing_twice['id']:
            weight -=5
        if float(x[1]['form']) ==0:
            weight=0
        if weight < 0:
            weight = 0
        x[1]['weight'] = weight
        df1 = df1.append(x[1])    
        df1=df1.sort_values('weight', ascending=False).iloc[0:10]
    return df1.sample(1, weights=df1.weight)