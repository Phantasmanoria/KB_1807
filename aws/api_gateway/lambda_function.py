import boto3, json, requests, emotion
from datetime import datetime
import decimal
from boto3.dynamodb.conditions import Key, Attr


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

    line_access_token = 'JOkWyWKuTBqnN0XbutrwHFXn1bivaIJE7TwBXBkLmPtKs/fU3n+5I93nE1V1o3ipR3kIyUBiYo7FHCTDNPMjTkRSu1G0/LB8G+C26aKI0X23BFQ7h0ai24tbhM8QRbzaa1o8XbfrzOiq70BhiJFaPQdB04t89/1O/w1cDnyilFU='
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
        "ID": str(ID), # P-Key
        "date": str(date), # P-key
        "text": str(text),
        "confidence": str(confidence),
        "deadline": str(deadline),
        }
    
    return [1, 'LINEDATA', data]


def nouse_sendmsg(event):
    
    return [2, str("Cce37b5fa7cee08e2840ecdafe30e2462"), str(event['ID'] + ': ' + event['trans'])]


def nouse_start(event): #会議の開始時に内容を送る「今日の議題はホニャララです」

    return [2, str("Cce37b5fa7cee08e2840ecdafe30e2462"), str('「議題内容」: ' + event['trans'][6:-2])]


def nouse_end(event): #会議の終了時の声掛け

    return [2, str("Cce37b5fa7cee08e2840ecdafe30e2462"), str('「議論の終了時間が来ました」')]



def used_info(event):
    dataset = []

    jsonstr = json.dumps(event, indent=2)
    
    timestamp = event['events'][0]['timestamp']
    print("timestamp: " + str(timestamp))

    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("LINE") # DynamoDBのテーブル名

    # DynamoDBへのPut処理実行
    table.put_item(
      Item = {
          "timestamp": str(timestamp), # Partition Keyのデータ
        "message": jsonstr
      }
    )

#    dataset.append([2, str("Cce37b5fa7cee08e2840ecdafe30e2462"), str("line message")]) 
    if event['events'][0]['message'].get('text') != None: #LINEのメッセージ確認    
        if 'key:' in event['events'][0]['message']['text']: #keyがあればkey登録
            dataset.append(used_uid(event))
        if 'log:' in event['events'][0]['message']['text']: #logがあればlog出力
            used_log(event)
    
    return     dataset


def used_uid(event): # 音声入力時のIDとuserIdを関連付ける
    
    data = {
        "name": str(str(event['events'][0]['message']['text'])[4:]), # P-Key
        "uID": str(event['events'][0]['source']['userId']), # P-key
        }
    
    return [1, 'LINEUID', data]


def used_log(event): #指定したログの会話を持ってくる
    
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("LINEDATA") # DynamoDBのテーブル名

    response = table.query(
        KeyConditionExpression=Key('ID').eq(str(event['events'][0]['message']['text'])[4:]) & Key('date').ne('error')
    )

    for i in response['Items']:
        print(i['ID'], ":", i['text'])

    return [2, event['events'][0]['source']['userId'], str("test")]
