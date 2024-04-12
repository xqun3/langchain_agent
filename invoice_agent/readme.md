## 1、安装相关包

pip install -r requirements.txt 

## 填充运行变量

bucket = ""  #Name of bucket with data file and OpenAPI file
SENDER = ""  #Sender email address
KNOWLEDGEB_BASE_ID=""

## 2、运行

```
cd src
streamlit run ui.py
# 或者
python core_xml_agent3_dynamodb.py
```