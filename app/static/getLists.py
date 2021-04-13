import time
import pymongo
import toml
from static import xlogger
from pyquery import PyQuery as pq

config = toml.load('config.toml')
logger = xlogger.get_my_logger(__name__)
GRAB_INTERVAL = config['app']['GRAB_INTERVAL']

dbClient = pymongo.MongoClient(
    'mongodb://%s:%s@%s/' % (config['database']['user'],
                             config['database']['password'],
                             config['database']['address'])
)
myDB = dbClient[config['database']['name']]

header = {
    'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'
}
url = 'https://www.zhibo8.cc/'


def writeDB(gameList: list, teamList: set):
    if gameList:
        myDB.drop_collection('gameList')
        myDB.drop_collection('dataUpdate')
        myDB.drop_collection('teamList')
    now = time.time()
    myDB.dataUpdate.insert_one({
        'timestamp': now,
        'updateTime': time.strftime("%Y-%m-%d %H:%M", time.localtime(now))
    })
    myDB.teamList.insert_one({
        'teamList': list(teamList)
    })
    result = myDB.gameList.insert_many(gameList)
    logger.warning('inserted %d games' % (len(result.inserted_ids),))


def getPage():
    for retry in range(5):
        try:
            rqs = pq(url, headers=header, encoding='utf-8')
            return rqs
        except Exception as e:
            logger.warning('通过失败，重新尝试... %s' % e)
            continue
    logger.error('检查是否可以打开%s' % url)
    input('输入回车结束程序...')
    return []


def grabGameList():
    gameList = []
    teamList = set()
    logger.debug(url)
    try:
        page = getPage()
        allGame = page('div.content li').items()
    except Exception as e:
        logger.critical(e)
        allGame = None
    for game in allGame:
        gameLabel = game('li')
        teamInfo = game('b')
        if gameLabel.attr('label') and len(teamInfo.text().split()) > 1:
            teamList = set(gameLabel.attr('label').split(',')) | teamList
            try:
                gameInfo = {
                    'ID': gameLabel.attr('id'),
                    'Labels': gameLabel.attr('label').split(','),
                    'Time': gameLabel.attr('data-time').split(),
                    # 'Show Time': showTime(gameLabel.attr('data-time').split()),
                    'Team1': teamInfo.text().split()[1],
                    # 'Team1 Logo': 'https:' + teamInfo('img:first').attr('src'),
                    'Team2': teamInfo.text().split()[-1],
                    # 'Team2 Logo': 'https:' + teamInfo('img:last').attr('src'),
                    'Broadcast': game('a:first').text().split()
                }
            except AttributeError:
                return
            gameList.append(gameInfo)
    # with open('gameList.json', 'w', encoding='utf-8') as jsonSave:
    #     json.dump(gameList, jsonSave, ensure_ascii=False, indent=4)
    writeDB(gameList, teamList)
    return


def getGameList() -> list:
    now = time.time()
    lastUpdate = myDB.dataUpdate.find_one()  # {'timestamp': {'$gt': 1.0}}
    if not lastUpdate or now - lastUpdate['timestamp'] > GRAB_INTERVAL:
        grabGameList()
    else:
        logger.info('No need to grab...')
    result = list(myDB.gameList.aggregate([{
        '$sort': {
            'Time.0': 1,
            'Time.1': 1
        }
    }]))
    for d in result:
        del d['_id']
    # logger.warning(teams)
    return result


def getTeamList() -> list:
    teams = myDB.teamList.find_one()
    if teams['teamList']:
        return teams['teamList']
    else:
        return []


if __name__ == '__main__':
    getGameList()
