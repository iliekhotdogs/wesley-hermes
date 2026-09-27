import sys, os
sys.path.insert(0, os.path.join(os.environ.get('HERMES_HOME', os.path.expanduser('~/.hermes')), 'skills', 'productivity', 'google-workspace', 'scripts'))
from google_api import get_credentials
from googleapiclient.discovery import build
SID='1qjJT4B3YvtSJflW9nZvhqG66Fp_tTbcPeCJObzjop1k'
s=build('sheets','v4',credentials=get_credentials())
meta=s.spreadsheets().get(spreadsheetId=SID).execute()
found=next((x['properties'] for x in meta['sheets'] if x['properties']['title']=='CIBC Import'),None)
if not found:
    s.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':[{'addSheet':{'properties':{'title':'CIBC Import'}}}]}).execute()
    meta=s.spreadsheets().get(spreadsheetId=SID).execute()
    found=next(x['properties'] for x in meta['sheets'] if x['properties']['title']=='CIBC Import')
i=found['sheetId']
s.spreadsheets().values().clear(spreadsheetId=SID,range='CIBC Import!A1:H100',body={}).execute()
values=[
 ['CIBC TRANSACTION IMPORT','','','','','','',''],
 ['Paste the downloaded CIBC CSV below starting at A7. Keep this tab as the raw staging area; manually copy cleaned rows into Input.','','','','','','',''],
 ['CIBC Online Banking: More → Download Transactions → choose your debit account and date range → CSV.','','','','','','',''],
 ['Suggested mapping into Input: CIBC Date → Date | Description → Place/Notes | Debit → negative Amount | Credit → positive Amount | manually choose Category.','','','','','','',''],
 ['Do not paste over this instruction area.','','','','','','',''],
 ['','','','','','','',''],
 ['Date','Description','Debit','Credit','Amount to Input','Category','Place','Notes'],
]
s.spreadsheets().values().update(spreadsheetId=SID,range='CIBC Import!A1:H7',valueInputOption='USER_ENTERED',body={'values':values}).execute()
orange={'red':1.0,'green':0.6,'blue':0.0}; navy={'red':0.07,'green':0.12,'blue':0.22}; cream={'red':1.0,'green':0.98,'blue':0.92}; white={'red':1.0,'green':1.0,'blue':1.0}
req=[
 {'repeatCell':{'range':{'sheetId':i,'startRowIndex':0,'endRowIndex':1,'startColumnIndex':0,'endColumnIndex':8},'cell':{'userEnteredFormat':{'backgroundColor':navy,'textFormat':{'bold':True,'fontSize':16,'foregroundColor':white}}},'fields':'userEnteredFormat(backgroundColor,textFormat)'}},
 {'repeatCell':{'range':{'sheetId':i,'startRowIndex':1,'endRowIndex':5,'startColumnIndex':0,'endColumnIndex':8},'cell':{'userEnteredFormat':{'backgroundColor':cream,'wrapStrategy':'WRAP'}},'fields':'userEnteredFormat(backgroundColor,wrapStrategy)'}},
 {'repeatCell':{'range':{'sheetId':i,'startRowIndex':6,'endRowIndex':7,'startColumnIndex':0,'endColumnIndex':8},'cell':{'userEnteredFormat':{'backgroundColor':orange,'textFormat':{'bold':True}}},'fields':'userEnteredFormat(backgroundColor,textFormat)'}},
 {'updateSheetProperties':{'properties':{'sheetId':i,'gridProperties':{'frozenRowCount':7}},'fields':'gridProperties.frozenRowCount'}},
]
for c,px in enumerate([115,250,110,110,135,150,180,300]): req.append({'updateDimensionProperties':{'range':{'sheetId':i,'dimension':'COLUMNS','startIndex':c,'endIndex':c+1},'properties':{'pixelSize':px},'fields':'pixelSize'}})
# Formula helper: combines debit/credit into an Input-ready signed amount for pasted rows.
req.append({'repeatCell':{'range':{'sheetId':i,'startRowIndex':7,'endRowIndex':100,'startColumnIndex':4,'endColumnIndex':5},'cell':{'userEnteredFormat':{'numberFormat':{'type':'CURRENCY','pattern':'$#,##0.00'}}},'fields':'userEnteredFormat.numberFormat'}})
s.spreadsheets().batchUpdate(spreadsheetId=SID,body={'requests':req}).execute()
# Fill helper formulas down the staging area.
formulas=[[f'=IF(A{r}="","",N(D{r})-N(C{r}))'] for r in range(8,101)]
s.spreadsheets().values().update(spreadsheetId=SID,range='CIBC Import!E8:E100',valueInputOption='USER_ENTERED',body={'values':formulas}).execute()
print('CIBC Import staging tab created.')
