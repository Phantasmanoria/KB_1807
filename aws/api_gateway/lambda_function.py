import boto3, json, requests, emotion, os
from datetime import datetime
import decimal
from boto3.dynamodb.conditions import Key, Attr

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
            return super(DecimalEncoder, self).default(o)
                                                        

print('Loading function')      # Functionのロードをログに出力

def lambda_handler(event, context):

    mode = 0 #正規データ(マイクorLINE)の検査

    if event.get('ID') != None: #マイク
        print("direct voice sending")
        command = nouse_info(event)
        mode = 1
        
    if event.get('events') != None: #LINE
        print("LINE message sending")
        command = used_info(event)
        mode = 1

    if mode == 1: #command内の配列にしたがってデータを実行
        for item in command:
            if item[0] == 1:
                senddb(item[1], item[2])
            elif item[0] == 2:
                sendmessage(item[1], item[2])
    
    return event


def senddb (table, data):
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(table) # DynamoDBのテーブル名

    # DynamoDBへのPut処理実行
    table.put_item(
        Item = data
    )

    
def sendmessage(ugID,text):
    # 文字列へ変換

    line_access_token = os.environ['LINE_ACCESS_TOKEN']
    line_push_api = 'https://api.line.me/v2/bot/message/push'
    messages = [
        {
            "type": str("text"),
            "text": str(text) #textをここに入力
        }
    ]
    payload = {
        "to": str(ugID), #IDをここに入力
        "messages": messages
    }
    header = {
        "Content-Type": "application/json",
        "Authorization": 'Bearer ' + line_access_token #アクセス権限を付随
    }  # 発行したトークン
    
    body = json.dumps(payload) #bodyをJSON形式に変換
    requests.post(line_push_api, data=body, headers=header) #送信



def nouse_info(event):
    dataset = [] #配列に更に配列を入れる
        
    dataset.append(nouse_pushdb(event))
    if '今日の議題は' in event['trans']:
        dataset.append(nouse_start(event))
    else:
        dataset.append(nouse_sendmsg(event))

    if str(event['finish']) == 'True':
        dataset.append(nouse_end(event))
        
    return dataset


def nouse_pushdb(event):
    
    ID = event['ID']
    print("ID: " + str(ID))
    date = event['time']
    print("date: " + str(date))
    text = event['trans']
    print("text: " + str(text))
    confidence = event['confidence']
    print("confidence: " + str(confidence))
    deadline = event['finish']
    print("deadline: " + str(deadline))

    data = {
        "from": "mic",
        "ID": str(ID), # P-Key
        "date": str(date), # P-key
        "text": str(text),
        "confidence": str(confidence),
        "deadline": str(deadline),
        }
    
    return [1, os.environ['MIC_DB'], data]


def nouse_sendmsg(event):
    
    return [2, os.environ['DEFAULT_GID'], str(event['ID'] + ': ' + event['trans'])]


def nouse_start(event): #会議の開始時に内容を送る「今日の議題はホニャララです」

    return [2, os.environ['DEFAULT_GID'], str('「議題内容」: ' + event['trans'][6:-2])]


def nouse_end(event): #会議の終了時の声掛け

    return [2, os.environ['DEFAULT_GID'], str('「議論の終了時間が来ました」')]



def used_info(event):
    dataset = []

    jsonstr = json.dumps(event, indent=2)
    
    timestamp = event['events'][0]['timestamp']
    print("timestamp: " + str(timestamp))

    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(os.environ['LINE_DB']) # DynamoDBのテーブル名

    # DynamoDBへのPut処理実行
    table.put_item(
      Item = {
          "timestamp": str(timestamp), # Partition Keyのデータ
        "message": jsonstr
      }
    )

#    dataset.append([2, str(""), str("line message")]) 
    if event['events'][0]['message'].get('text') != None: #LINEのメッセージ確認    
        if 'key:' in event['events'][0]['message']['text']: #keyがあればkey登録
            dataset.append(used_uid(event))
        if 'log:' in event['events'][0]['message']['text']: #logがあればlog出力
            dataset.append(used_log(event))
        dataset.append([2, str(event['events'][0]['source']['groupId']), str(event['events'][0]['message']['text'])])
    return     dataset


def used_uid(event): # 音声入力時のIDとuserIdを関連付ける
    
    data = {
        "check": os.environ['CHECK_KEY'],
        "name": str(str(event['events'][0]['message']['text'])[4:]), # P-Key
        "uID": str(event['events'][0]['source']['userId']), # P-key
        }
    
    return [1, os.environ['UID_INFO'], data]


def used_log(event): #指定したログの会話を持ってくる
    
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table(os.environ['MIC_DB']) # DynamoDBのテーブル名

    response = table.query(
        KeyConditionExpression=Key('from').eq('mic')
    )

    msg = ''
    
    for i in response['Items']:
        if i['ID'] == str(event['events'][0]['message']['text'])[4:]:
            msg = msg + str(i['ID']) + '(' + str(i['date']) + "): " + str(i['text']) + "\n"

    return [2, str(event['events'][0]['source']['userId']), str(msg)]

