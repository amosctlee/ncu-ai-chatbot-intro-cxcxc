#!/usr/bin/env python
# coding: utf-8

# In[ ]:


# !pip install flask
# !pip install line-bot-sdk
# !pip install gspread
# !pip install peewee
# !pip install --upgrade azure-cognitiveservices-vision-face


# In[ ]:


'''

整體功能描述

應用伺服器主結構樣板
    用來定義使用者傳送消息時，應該傳到哪些方法上
        比如收到文字消息時，轉送到文字專屬處理方法

消息專屬方法定義
    當收到文字消息，從資料夾內提取消息，並進行回傳。
    
啟動應用伺服器    


'''


# In[ ]:


'''

Application 主架構

'''

# 引用Web Server套件
from flask import Flask, request, abort

# 從linebot 套件包裡引用 LineBotApi 與 WebhookHandler 類別
from linebot import (
    LineBotApi, WebhookHandler
)

# 引用無效簽章錯誤
from linebot.exceptions import (
    InvalidSignatureError
)

# 載入json處理套件
import json

# 載入臉部辨識套件
from io import BytesIO
from PIL import Image, ImageDraw
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials


# 載入基礎設定檔
secretFileContentJson=json.load(open("./line_secret_key",'r',encoding='utf8'))

# 設定Server啟用細節
app = Flask(__name__,static_url_path = "/material" , static_folder = "./material/")

# 生成實體物件
line_bot_api = LineBotApi(secretFileContentJson.get("channel_access_token"))
handler = WebhookHandler(secretFileContentJson.get("secret_key"))

# Create an authenticated FaceClient.
KEY = secretFileContentJson.get("azure_key_1")
ENDPOINT = secretFileContentJson.get("azure_face_detect_endpoint")
face_client = FaceClient(ENDPOINT, CognitiveServicesCredentials(KEY))


# 啟動server對外接口，使Line能丟消息進來
@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# In[ ]:


'''

消息判斷器

讀取指定的json檔案後，把json解析成不同格式的SendMessage

讀取檔案，
把內容轉換成json
將json轉換成消息
放回array中，並把array傳出。

'''

# 引用會用到的套件
from linebot.models import (
    ImagemapSendMessage,TextSendMessage,ImageSendMessage,LocationSendMessage,FlexSendMessage,VideoSendMessage
)

from linebot.models.template import (
    ButtonsTemplate,CarouselTemplate,ConfirmTemplate,ImageCarouselTemplate
    
)

from linebot.models.template import *

def detect_json_array_to_new_message_array(fileName):
    
    #開啟檔案，轉成json
    with open(fileName,'r',encoding='utf8') as f:
        jsonArray = json.load(f)
    
    # 解析json
    returnArray = []
    for jsonObject in jsonArray:

        # 讀取其用來判斷的元件
        message_type = jsonObject.get('type')
        
        # 轉換
        if message_type == 'text':
            returnArray.append(TextSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'imagemap':
            returnArray.append(ImagemapSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'template':
            returnArray.append(TemplateSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'image':
            returnArray.append(ImageSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'sticker':
            returnArray.append(StickerSendMessage.new_from_json_dict(jsonObject))  
        elif message_type == 'audio':
            returnArray.append(AudioSendMessage.new_from_json_dict(jsonObject))  
        elif message_type == 'location':
            returnArray.append(LocationSendMessage.new_from_json_dict(jsonObject))
        elif message_type == 'flex':
            returnArray.append(FlexSendMessage.new_from_json_dict(jsonObject))  
        elif message_type == 'video':
            returnArray.append(VideoSendMessage.new_from_json_dict(jsonObject))    


    # 回傳
    return returnArray


# In[ ]:


"""
認證
使用剛剛建立並下載的JSON檔案

"""

import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

# 填寫金鑰檔案位置、名稱
credentials = Credentials.from_service_account_file('ncu-ai-tutorial-47520ee70490.json', 
                                                    scopes=scopes)

gc = gspread.authorize(credentials)
spread_sheet = gc.open('Linebot_records')


# In[ ]:



'''

handler處理關注消息

用戶關注時，讀取 素材 -> 關注 -> reply.json

將其轉換成可寄發的消息，傳回給Line

將用戶資料存在Google sheet

'''

# 引用套件
from linebot.models import (
    FollowEvent
)

# 關注事件處理
@handler.add(FollowEvent)
def process_follow_event(event):
    
    # 讀取並轉換
    result_message_array =[]
    replyJsonPath = "material/follow/reply.json"
    result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

    # 消息發送
    line_bot_api.reply_message(
        event.reply_token,
        result_message_array
    )

    # 從follow資料夾內，取出圖文選單id，並告知line，綁定用戶
    linkRichMenuId = open("material/follow/rich_menu_id", 'r').read()
    line_bot_api.link_rich_menu_to_user(event.source.user_id, linkRichMenuId)
    
    
    # 準備將FollowEvent 內容存入FollowEventTable
    follow_wks = spread_sheet.worksheet('FollowEventTable')
    values_to_follow_wks = [event.reply_token,
                            event.timestamp,
                            event.source.user_id]
    print(follow_wks.append_row(values_to_follow_wks))
    
    
    # 用user_id 透過line_bot_api 向LINE官方索取用戶個資
    user_profile = line_bot_api.get_profile(event.source.user_id)
    
    # 準備將用戶資料存入(或更新) LineUserProfileTable
    users_wks = spread_sheet.worksheet('LineUserProfileTable')
    values_to_users_wks = [user_profile.user_id,
                          user_profile.display_name if user_profile.display_name else "",
                          user_profile.picture_url if user_profile.picture_url else "",
                          user_profile.status_message if user_profile.status_message else ""]

    # 如果LineUserProfileTable 中沒有此用戶則新增
    if not users_wks.findall(event.source.user_id):
        print(users_wks.append_row(values_to_users_wks))
        
    # 如果LineUserProfileTable 中已存在此用戶則更新
    else:
        # 取得儲存格的 A1 notation
        cell_adrs = users_wks.find(event.source.user_id).address
        # 取數字，ex: A1 -> 1
        cell_adrs = cell_adrs[1:]
        print(users_wks.update(f"A{cell_adrs}:D{cell_adrs}", [values_to_users_wks]))


# In[ ]:



'''

handler處理文字消息

收到用戶回應的文字消息，
按文字消息內容，往素材資料夾中，找尋以該內容命名的資料夾，讀取裡面的reply.json

轉譯json後，將消息回傳給用戶

將用戶文字消息存在Google sheet

'''

# 引用套件
from linebot.models import (
    MessageEvent, TextMessage
)

# 文字消息處理
@handler.add(MessageEvent,message=TextMessage)
def process_text_message(event):
    
    # 將用戶的文字消息存進TextMessageTable
    text_wks = spread_sheet.worksheet('TextMessageTable')
    values_to_text_wks = [event.reply_token,
                         event.timestamp,
                         event.source.user_id,
                         event.message.id,
                         event.message.type,
                         event.message.text]
    print(text_wks.append_row(values_to_text_wks))

    # 讀取本地檔案，並轉譯成消息
    result_message_array =[]
    replyJsonPath = "material/"+event.message.text+"/reply.json"
    result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

    # 發送
    line_bot_api.reply_message(
        event.reply_token,
        result_message_array
    )
    

    


# In[ ]:


'''

handler處理Postback Event

載入功能選單與啟動特殊功能

解析postback的data，並按照data欄位判斷處理

現有三個欄位
menu, folder, tag

若folder欄位有值，則
    讀取其reply.json，轉譯成消息，並發送

若menu欄位有值，則
    讀取其rich_menu_id，並取得用戶id，將用戶與選單綁定
    讀取其reply.json，轉譯成消息，並發送
    
將用戶PostbackEvent 中的data存在Google sheet

'''
from linebot.models import (
    PostbackEvent
)

from urllib.parse import parse_qs 

@handler.add(PostbackEvent)
def process_postback_event(event):
    query_string_dict = parse_qs(event.postback.data)
    print(query_string_dict)
    
    # 將用戶產生的PostbackEvent 存進PostbackEventTable
    postback_wks = spread_sheet.worksheet('PostbackEventTable')
    values_to_postback_wks = [event.reply_token,
                             event.timestamp,
                             event.source.user_id,
                             event.postback.data]
    print(postback_wks.append_row(values_to_postback_wks))
    
    # 準備將用戶回答問卷的答案存進QuestionsAnswer
    qa_wks = spread_sheet.worksheet('QuestionsAnswer')
    
    # 如果還沒回答過問卷，新增一列資料
    print(qa_wks.findall(event.source.user_id))
    if not qa_wks.findall(event.source.user_id):
        values_to_qa_wks = [event.source.user_id,
                           query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q1' else "",
                           query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q2' else "",
                           query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q3' else "",
                           query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q4' else ""]
        print(qa_wks.append_row(values_to_qa_wks))
    
    # 已經回答過問卷，則根據回答的題目更新資料
    else:
        # 取得儲存格的 A1 notation
        cell_adrs = qa_wks.find(event.source.user_id).address
        # 取數字，ex: A1 -> 1
        cell_adrs = cell_adrs[1:]
        # 從query_string_dict 取出題號，並根據題號存入答案
        if query_string_dict.get('question')[0] == 'q1':
            print(qa_wks.update(f"B{cell_adrs}", query_string_dict.get('answer')[0]))
        elif query_string_dict.get('question')[0] == 'q2':
            print(qa_wks.update(f"C{cell_adrs}", query_string_dict.get('answer')[0]))
        elif query_string_dict.get('question')[0] == 'q3':
            print(qa_wks.update(f"D{cell_adrs}", query_string_dict.get('answer')[0]))
        elif query_string_dict.get('question')[0] == 'q4':
            print(qa_wks.update(f"E{cell_adrs}", query_string_dict.get('answer')[0]))
    
    
    if 'folder' in query_string_dict:
    
        result_message_array =[]

        replyJsonPath = 'material/'+query_string_dict.get('folder')[0]+"/reply.json"
        result_message_array = detect_json_array_to_new_message_array(replyJsonPath)
  
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )
    elif 'menu' in query_string_dict:
 
        linkRichMenuId = open("material/"+query_string_dict.get('menu')[0]+'/rich_menu_id', 'r').read()
        line_bot_api.link_rich_menu_to_user(event.source.user_id,linkRichMenuId)
        
        replyJsonPath = 'material/'+query_string_dict.get('menu')[0]+"/reply.json"
        result_message_array = detect_json_array_to_new_message_array(replyJsonPath)
  
        line_bot_api.reply_message(
            event.reply_token,
            result_message_array
        )
    
    


# In[ ]:


# """
# 定義並創建資料庫中的表格，以便後續將資料存入資料庫
#     LineUserProfileTable
#     FollowEventTable
#     TextMessageTable
#     PostbackEventTable
#     QuestionsAnswer

# """

# import peewee
# import datetime

# # 建立資料庫連線
# db = peewee.PostgresqlDatabase(secretFileContentJson.get("pg_db"), 
#                         user=secretFileContentJson.get("pg_user"), 
#                         password=secretFileContentJson.get("pg_password"),
#                         host=secretFileContentJson.get("pg_host"), 
#                         port=secretFileContentJson.get("pg_port"))


# class BaseModel(peewee.Model):
#     class Meta:
#         database = db
        
# # 定義資料表
# class LineUserProfileTable(BaseModel):
#     # 定義欄位
#     userId = peewee.CharField()
#     displayName = peewee.CharField()
#     pictureUrl = peewee.CharField()
#     statusMessage = peewee.CharField(default="null")

        
# # 定義資料表
# class FollowEventTable(BaseModel):
#     # 定義欄位
#     replyToken = peewee.CharField()
#     timestamp = peewee.TimestampField()
#     userId = peewee.CharField()
        
# # 定義資料表
# class TextMessageTable(BaseModel):
#     # 定義欄位
#     replyToken = peewee.CharField()
#     timestamp = peewee.TimestampField()
#     userId = peewee.CharField()
    
#     messageId = peewee.CharField()
#     messageType = peewee.CharField()
#     messageText = peewee.CharField()
        
# # 定義資料表
# class PostbackEventTable(BaseModel):
#     # 定義欄位
#     replyToken = peewee.CharField()
#     timestamp = peewee.TimestampField()
#     userId = peewee.CharField()
    
#     postbackData = peewee.CharField()
    
# # 定義資料表
# class QuestionsAnswer(BaseModel):
#     userId = peewee.CharField()
#     question_1 = peewee.CharField()
#     question_2 = peewee.CharField()
#     question_3 = peewee.CharField()
#     question_4 = peewee.CharField()
    
# # db.drop_tables([LineUserProfileTable, FollowEventTable, TextMessageTable, PostbackEventTable, QuestionsAnswer])
# db.create_tables([LineUserProfileTable, FollowEventTable, TextMessageTable, PostbackEventTable, QuestionsAnswer])

# if db:
#     db.close()


# In[ ]:


# '''

# handler處理關注消息

# 用戶關注時，讀取 素材 -> 關注 -> reply.json

# 將其轉換成可寄發的消息，傳回給Line

# 將用戶資料收進資料庫

# '''

# # 引用套件
# from linebot.models import (
#     FollowEvent
# )

# # 關注事件處理
# @handler.add(FollowEvent)
# def process_follow_event(event):
    
#     # 讀取並轉換
#     result_message_array =[]
#     replyJsonPath = "material/follow/reply.json"
#     result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

#     # 消息發送
#     line_bot_api.reply_message(
#         event.reply_token,
#         result_message_array
#     )

#     # 從follow資料夾內，取出圖文選單id，並告知line，綁定用戶
#     linkRichMenuId = open("material/follow/rich_menu_id", 'r').read()
#     line_bot_api.link_rich_menu_to_user(event.source.user_id, linkRichMenuId)
    
#     # 將收集到的資料存進資料庫
#     user_profile = line_bot_api.get_profile(event.source.user_id)
    

#     with db:
#         # 存入FolloweEvent
#         FollowEventTable.create(replyToken=event.reply_token, 
#                                 timestamp=event.timestamp, 
#                                 userId=event.source.user_id)
        
#         # 存入個資
#         try:
#             # 判斷此用戶是否已經記錄過
#             record_of_users = LineUserProfileTable.select().where(LineUserProfileTable.userId == event.source.user_id).get()
#         except:
#             record_of_users = None
#         print(record_of_users)

#         if record_of_users is None:
#             # 用戶不存在時新增
#             LineUserProfileTable.create(userId=user_profile.user_id, 
#                                         displayName=user_profile.display_name if user_profile.display_name else "",
#                                         pictureUrl=user_profile.picture_url if user_profile.picture_url else "", 
#                                         statusMessage=user_profile.status_message if user_profile.status_message else "")
#         else:
#             # 用戶存在時更新
#             record_of_users.displayName = user_profile.display_name if user_profile.display_name else ""
#             record_of_users.pictureUrl =  user_profile.picture_url if user_profile.picture_url else ""
#             record_of_users.statusMessage =  user_profile.status_message if user_profile.status_message else ""
#             record_of_users.save()


# In[ ]:


# '''

# handler處理文字消息

# 收到用戶回應的文字消息，
# 按文字消息內容，往素材資料夾中，找尋以該內容命名的資料夾，讀取裡面的reply.json

# 轉譯json後，將消息回傳給用戶

# 將用戶發話記錄收集進資料庫

# '''

# # 引用套件
# from linebot.models import (
#     MessageEvent, TextMessage
# )

# # 文字消息處理
# @handler.add(MessageEvent,message=TextMessage)
# def process_text_message(event):
    
#     try:
#         # 讀取本地檔案，並轉譯成消息
#         result_message_array =[]
#         replyJsonPath = "material/"+event.message.text+"/reply.json"
#         result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

#         # 發送
#         line_bot_api.reply_message(
#             event.reply_token,
#             result_message_array
#         )
#     except FileNotFoundError as e:
#         # 用戶回傳文字不一定會觸發到我們預定的資料夾
#         print("file not found!")
    
#     # 將收集到的資料存進資料庫
#     with db:
#         TextMessageTable.create(replyToken=event.reply_token, 
#                                 timestamp=event.timestamp, 
#                                 userId=event.source.user_id, 
#                                 messageId=event.message.id, 
#                                 messageType=event.message.type, 
#                                 messageText=event.message.text)


# In[ ]:


# '''

# handler處理Postback Event

# 載入功能選單與啟動特殊功能

# 解析postback的data，並按照data欄位判斷處理

# 現有三個欄位
# menu, folder, tag

# 若folder欄位有值，則
#     讀取其reply.json，轉譯成消息，並發送

# 若menu欄位有值，則
#     讀取其rich_menu_id，並取得用戶id，將用戶與選單綁定
#     讀取其reply.json，轉譯成消息，並發送



# '''
# from linebot.models import (
#     PostbackEvent
# )

# from urllib.parse import parse_qs 

# @handler.add(PostbackEvent)
# def process_postback_event(event):
    
#     # 解析data欄位的內容
#     query_string_dict = parse_qs(event.postback.data)
    
#     print(query_string_dict)
    
#     # 若folder欄位存在
#     if 'folder' in query_string_dict:
    
#         result_message_array =[]
        
#         # 偵測material資料夾內，與folder欄位的內容相同名的資料夾內的reply.json
#         replyJsonPath = 'material/'+query_string_dict.get('folder')[0]+"/reply.json"
        
#         # 轉換成Line需要的消息格式
#         result_message_array = detect_json_array_to_new_message_array(replyJsonPath)

#         line_bot_api.reply_message(
#             event.reply_token,
#             result_message_array
#         )
        
#     # 若前面的欄位都不存在，且menu欄位存在
#     elif 'menu' in query_string_dict:
 
#         linkRichMenuId = open("material/"+query_string_dict.get('menu')[0]+'/rich_menu_id', 'r').read()
#         line_bot_api.link_rich_menu_to_user(event.source.user_id,linkRichMenuId)
        
#         replyJsonPath = 'material/'+query_string_dict.get('menu')[0]+"/reply.json"
#         result_message_array = detect_json_array_to_new_message_array(replyJsonPath)
  
#         line_bot_api.reply_message(
#             event.reply_token,
#             result_message_array
#         )
    
#     # 將收集到的資料存進資料庫
#     with db:
#         # 存入postbackevent
#         PostbackEventTable.create(replyToken=event.reply_token,
#                                   timestamp=event.timestamp, 
#                                   userId=event.source.user_id, 
#                                   postbackData=event.postback.data)
        
#         # 存入問卷答案
#         try:
#             # 判斷是否已經回答過
#             record_of_questions = QuestionsAnswer.select().where(QuestionsAnswer.userId == event.source.user_id).get()
#         except:
#             record_of_questions = None
#         print(record_of_questions)
        
#         if record_of_questions is None:
#             # 還沒回答過
#             QuestionsAnswer.create(userId=event.source.user_id,
#                                   question_1=query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q1' else "", 
#                                   question_2=query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q2' else "", 
#                                   question_3=query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q3' else "",
#                                   question_4=query_string_dict.get('answer')[0] if query_string_dict.get('question')[0] == 'q4' else "")
#         else:
#             # 已經回答過
#             if query_string_dict.get('question')[0] == 'q1':
#                 record_of_questions.question_1 = query_string_dict.get('answer')[0]
#             elif query_string_dict.get('question')[0] == 'q2':
#                 record_of_questions.question_2 = query_string_dict.get('answer')[0]
#             elif query_string_dict.get('question')[0] == 'q3':
#                 record_of_questions.question_3 = query_string_dict.get('answer')[0]
#             elif query_string_dict.get('question')[0] == 'q4':
#                 record_of_questions.question_4 = query_string_dict.get('answer')[0]
#             record_of_questions.save()


# In[ ]:


'''

handler處理圖片消息

用戶傳照片消息給Line

我方使用 消息的id 向Line 索取照片

辨識照片中的臉，並回傳辨識後的照片

'''

from linebot.models import (
    MessageEvent, TextSendMessage,ImageMessage, ImageSendMessage
)
from urllib.parse import urljoin


@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    
    # 開始臉部辨識
    detected_faces = face_client.face.detect_with_stream(BytesIO(message_content.content))
    
    if not detected_faces:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="找不到臉....")
        )
        raise Exception('No face detected from image...')

    # Convert width height to a point in a rectangle
    def getRectangle(faceDictionary):
        rect = faceDictionary.face_rectangle
        left = rect.left
        top = rect.top
        right = left + rect.width
        bottom = top + rect.height

        return ((left, top), (right, bottom))

    img = Image.open(BytesIO(message_content.content))

    # For each face returned use the face rectangle and draw a red box.
    print('Drawing rectangle around face...')
    draw = ImageDraw.Draw(img)
    for face in detected_faces:
        draw.rectangle(getRectangle(face), outline='red')

    # Display the image in the users default image browser.
    # img.show()
    # Save the image from users.
    img.save(f'./material/detected_images/{event.message.id}.jpg')
    
    # 準備要回傳的圖片 
    base_url = secretFileContentJson.get('base_url')
    detected_image_message_dict = {
        "type": "image",
        "originalContentUrl": urljoin(base_url, f'material/detected_images/{event.message.id}.jpg'),
        "previewImageUrl": urljoin(base_url, f'material/detected_images/{event.message.id}.jpg')
    }
    
    line_bot_api.reply_message(
        event.reply_token, 
        ImageSendMessage.new_from_json_dict(detected_image_message_dict)
    )


# In[ ]:


'''

Application 運行（開發版）

'''
# if __name__ == "__main__":
#     app.run(host='0.0.0.0')


# In[ ]:


'''

Application 運行（heroku版）

'''

import os
if __name__ == "__main__":
    app.run(host='0.0.0.0',port=os.environ['PORT'])


# In[ ]:




