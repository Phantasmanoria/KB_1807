import json, boto3
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
        
def lambda_handler(event, context):
    # TODO implement
    
    dynamoDB = boto3.resource("dynamodb")
    table = dynamoDB.Table("LINEDATA") # DynamoDBのテーブル名
    response = table.query(
        KeyConditionExpression=Key('ID').eq(str("sutyo"))
    )
    msg = ''
    
    for i in response['Items']:
        msg =  i['text']
        msg2 = msg.encode('utf-8_sig')
#    html = "<html><head></head>><body><script>print unescape(" + msg + ");</script></body></html>"
        html = "<html><head></head>><body>" + msg + "</body></html>"
        return html
        
