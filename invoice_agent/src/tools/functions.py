from typing import List,Dict,Union

import time
import logging
from typing import Dict,List,Union,Optional

from pydantic import BaseModel, Field,validator
from pydantic import BaseModel,ValidationInfo, field_validator, Field,ValidationError

import json
import time
import os
import boto3
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from fpdf import FPDF
from pathlib import Path
path = Path(__file__)

parrent_path = path.parent.parent
# current_path = os.path.abspath(__file__)
print(parrent_path)
from enum import Enum
logger = logging.getLogger(__name__)
credentials = boto3.Session().get_credentials()
aws_access_key_id = credentials.access_key # you can modify to your access_key 
aws_secret_access_key = credentials.secret_key  # you can modify to your secret_key 
s3 = boto3.client('s3', region_name='us-east-1', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
# bedrock_runtime = boto3.client("bedrock-")
knowledgebases_client = boto3.client("bedrock-agent-runtime", "us-east-1", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
bucket = ""  #Name of bucket with data file and OpenAPI file
SENDER = ""  #Sender email address
KNOWLEDGEB_BASE_ID=""

# font_lib = "../utils/DejaVuSansCondensed.ttf"
# current_path = os.path.abspath(__file__).
# print(current_path)
font_lib = f"{parrent_path}/utils/DejaVuSansCondensed.ttf"
print(font_lib)
local_product_name_map_file = f'{parrent_path.parent}/doc/product_code_name_map.txt' #Location of data file in S3
print(local_product_name_map_file)



## 2.generate_preview_invoice_image,issue_invoice
class InvoicemiddleInput(BaseModel):
    name: str = Field(description="The name of product",examples=["实木茶几"])
    code: str = Field(description="The code of product",examples=["1050201010000000000"])
    money: float = Field(description="The money of product",examples=[1000.0])
    
class InvoiceType(str, Enum):
    special_invoice = '全电专用发票'
    ordinary_invoice = '全电普通发票'

class InvoiceInput(BaseModel):
    product_detail: List[InvoicemiddleInput] = Field(description="The product details",
                                examples=[[{'name': '实木茶几', 'code': '1050201010000000000', 'money': 1000},
                                            {'name': '餐饮费用', 'code': '3070401000000000000', 'money': 500}]],
                                            )
    # product_detail: InvoicemiddleInput = Field(description="The product details",
    #                         examples=[{'name': '实木茶几', 'code': '1050201010000000000', 'money': 1000}])
    buyer_company_name: str = Field(description="The name of buyer company",examples=["广东唯一网络科技有限公司"])
    buyer_tax_number: str = Field(description="The tax number of buyer company",examples=["91450923MA5L7W2C1W"])
    invoice_type: Optional[str] = Field(description="The type of invoice",default="全电普通发票",enum=["全电普通发票","全电专用发票"])
    remark: Optional[str] = Field(default="",description="Remarks on the invoice")
    
    @validator('product_detail', pre=True)
    def type_check(cls, v):
        if isinstance(v, dict):
            return [v]
        if not isinstance(v, list):
            return eval(v)
            # raise ValueError('product_detail must be a list')
        return v

    # @validator('product_detail')
    # def type_check(cls, v):
    #     if not isinstance(v, list):
    #         raise ValueError('product_detail must be a list')
    #     return v
    
    @field_validator('product_detail')
    def validate_product_detail(cls, value:str,info: ValidationInfo):
        
        if len(value) == 0:
            raise ValueError(f'product detail must not be empty')
        return value
    
    @field_validator('buyer_company_name')
    def validate_buyer_company_name(cls, value:str,info: ValidationInfo):
        if len(value) == 0:
            raise ValueError(f'buyer company name must not be empty')
        return value

    @field_validator('buyer_tax_number')
    def validate_buyer_tax_number(cls, value:str,info: ValidationInfo):
        if len(value) == 0:
            raise ValueError(f'buyer tax number must not be empty')
        return value
    
## 3.send_invoice_email
class SendInvoiceEmailInput(BaseModel):
    invoice_code: str = Field(description="The invoice code",examples=['79707992'])
    invoice_number: str = Field(description="The invoice number",examples=['013002100111'])
    email_address: str = Field(description="The email address for receiving emails",examples=['111915271@163.com'])

## 4.knowledge_base_retrieve
class RetrieveKnowledgeBaseInput(BaseModel):
    query: str = Field(description="A query used for retrieval",examples=['增值税专用发票可以私自印刷，伪造吗'])

def create_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    print(font_lib)
    pdf.add_font('DejaVu', '', font_lib, uni=True)
    pdf.set_font('DejaVu', '', 14)
    # pdf.set_font("Arial", size=12)
    for key, value in data.items():
        logger.debug(key, value)
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=1, align="C")
    file_path = f"{parrent_path.parent}/tmp_file/invoice.pdf"
    pdf.output(file_path)
    logger.debug("invoice created sucessfully")
    s3.upload_file(file_path, bucket, "invoice.pdf")
    return  file_path

user_info = {
            "id": "000001",
            "name": "Xiaoqun",
            "email": "test1@163.com",
            "drawer": "Xiaoqun",
            "reviewer": "Sam",
            "payee": "Lili",
            "phone": "0755-0000000",
            "address": "Qiantan, Shanghai",
            "card_name": "Amazon",
            "card_number": "00000000000000",
            "company_name": "Amazon",
            "tax_number": "440301999999980"
}

## 函数设置
functions_configs = {
    "get_product_code":
        {
            "product_name_map_file": local_product_name_map_file,
        }
}

product_name_map = {}
product_tax_map = {}
with open(functions_configs["get_product_code"]["product_name_map_file"],encoding="utf-8") as f:
    for line in f.readlines():
        line = line.strip()
        if line:
            code,name,tax = line.split("\t")
            product_name_map[code] = name
            product_tax_map[code] = min([float(tax_ins.strip('%')) / 100 for tax_ins in tax.split("、")])


def send_eamil(recipient: str, s3_file_path: str):
    sender = SENDER
    RECIPIENT = recipient

    AWS_REGION = "us-east-1"
    SUBJECT = "Invoice Info"
    
    BODY_TEXT = "Hello,\r\nInvoice has been generated, please check out attachment."

    # Download the S3 file to a temporary location
    tmp_file_path = f'{parrent_path.parent}/tmp_file/' + os.path.basename(s3_file_path)
    logger.debug(tmp_file_path)
    # s3.download_file(bucket, s3_file_path, tmp_file_path)

    ATTACHMENT = tmp_file_path

    # The HTML body of the email.
    BODY_HTML = """\
    <html>
    <head></head>
    <body>
    <h1>Hello!</h1>
    <p>Invoice has been generated, please check out attachment.</p>
    </body>
    </html>
    """

    CHARSET = "utf-8"
    client = boto3.client('ses',region_name=AWS_REGION)
    msg = MIMEMultipart('mixed')

    msg['Subject'] = SUBJECT 
    msg['From'] = sender 
    msg['To'] = RECIPIENT

    msg_body = MIMEMultipart('alternative')
    textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    att = MIMEApplication(open(ATTACHMENT, 'rb').read())

    att.add_header('Content-Disposition','attachment',filename=os.path.basename(ATTACHMENT))
    msg.attach(msg_body)
    msg.attach(att)
    try:
        response = client.send_raw_email(
            Source=sender,
            Destinations=[
                RECIPIENT
            ],
            RawMessage={
                'Data':msg.as_string(),
            },
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        logger.debug(e.response['Error']['Message'])
        return {"errcode": e.response['Error']['Message']} 
    else:
        logger.debug("Email sent! Message ID:"),
        logger.debug(response['MessageId'])
        return {"errcode": "0000", "MessageId": response['MessageId']}


# class OpenAIFunctions:
class UsefullFunctions:
    
    @staticmethod
    def generate_preview_invoice_info(
            user_id: str,
            product_detail: List[Dict[str, Union[str, int, float]]],
            buyer_company_name: str,
            buyer_tax_number: str,
            invoice_type: str = "全电普通发票",
            remark: str = "") -> dict:
        """This function generates a preview invoice image"""
        try:
            args = InvoiceInput(product_detail=product_detail, buyer_company_name=buyer_company_name, buyer_tax_number=buyer_tax_number, invoice_type=invoice_type, remark=remark)
        except Exception as e:
            logger.debug(str(e))
            result = {
                    "input_args": {
                        "product_detail":product_detail,
                        "buyer_company_name": buyer_company_name,
                        "buyer_tax_number": buyer_tax_number,
                        "invoice_type": invoice_type,
                    },
                    "status": "faile",
                    "results": str(e)
                }
            return f"Function input invalid, ask user to provide the missing params."

        seller_company_name = user_info["company_name"]
        seller_tax_number = user_info["tax_number"]
        drawer = user_info.get("drawer", "")
        issue_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        temp_invoice_number = "00000000"
        new_res = {}
        new_res["input_args"] = {}

        seller_company_name = user_info["company_name"]
        seller_tax_number = user_info["tax_number"]
        drawer = user_info.get("drawer","")
        issue_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        temp_invoice_number = "00000000"
        new_res = {}
        new_res["input_args"] = {}
        new_res["input_args"]["product_detail"] = product_detail
        new_res["input_args"]["buyer_company_name"] = buyer_company_name
        new_res["input_args"]["buyer_tax_number"] = buyer_tax_number
        new_res["input_args"]["invoice_type"] = invoice_type
        new_res["input_args"]["remark"] = remark

        invoice_type_map = {"全电普通发票": "26", "全电专用发票": "27"}
        invoice_type_num = invoice_type_map.get(invoice_type, None)
        if invoice_type_num is None:
            new_res["status"] = "fail"
            new_res["results"] = f"发票种类<{invoice_type}>填错了，目前只支持'全电普通发票'和'全电专用发票'，请进行修改."
            return new_res
        
        itemlist = []
        invoice_amounts = 0
        tax_amounts = 0
        for product in product_detail:
            product = product.dict()
            logger.debug(product)
            product_total_amount = '{:.2f}'.format(product["money"]) 
            tax_rate = product_tax_map.get(product["code"], None)
            if tax_rate is None:
                new_res["status"] = "fail"
                new_res["results"] = f"您提供的商品<{product['product_name']}>的税收编码<{product['code']}>是错误的，请进行修改."
                return new_res
            product_amount = '{:.2f}'.format(float(product_total_amount) / (1 + tax_rate))  
            tax_amount = '{:.2f}'.format(float(product_amount) * tax_rate)
            invoice_amounts += float(product_amount)
            tax_amounts += float(tax_amount)

            itemlist.append({
                "goodsName": product["name"],
                "specModel": "",
                "unit": "",
                "num": "",
                "unitPrice": "",
                "detailAmount": product_amount,
                "taxRate": '{:.2f}'.format(tax_rate),
                "taxAmount": tax_amount,
                "zeroTaxRateFlag": ""
                })
        data = {
            "clientId": "testClinetId",
            "appName": "开票",
            "invoiceType": invoice_type_num,
            "invoiceNo": temp_invoice_number,
            "issueTime": issue_date,
            "buyerName": buyer_company_name,
            "buyerTaxNo": buyer_tax_number,
            "salerName": seller_company_name,
            "salerTaxNo": seller_tax_number,
            "remark": remark,
            "drawer": drawer,
            "invoiceAmount": '{:.2f}'.format(invoice_amounts),
            "totalTaxAmount": '{:.2f}'.format(tax_amounts),
            "totalAmount": '{:.2f}'.format(invoice_amounts+tax_amounts),
            "itemList": itemlist
        }

        result = {
                    "input_args": {
                        "product_detail":product_detail,
                        "buyer_company_name": buyer_company_name,
                        "buyer_tax_number": buyer_tax_number,
                        "invoice_type": invoice_type,
                    },
                    "status": "success",
                    "results": {
                        "text_info": data
                    }
                }

        return result


    @staticmethod
    def issue_invoice(
            user_id: str,
            product_detail: List[Dict[str, Union[str, int, float]]],
            buyer_company_name: str,
            buyer_tax_number: str,
            invoice_type: str = "全电普通发票",
            remark: str = "") -> dict:
        """This function is used to issue invoices"""

        ## 发票基础信息设置
        reviewer = user_info.get("reviewer", "")
        payee = user_info.get("payee", "")
        seller_address = user_info.get("address", "")
        seller_phone = user_info.get("phone", "")
        seller_account = user_info.get("card_name", "") + user_info.get("card_number", "")
        seller_cardname = user_info.get("card_name", "")
        seller_cardnumber = user_info.get("card_number", "")
        seller_tax_number = user_info["tax_number"]
        #初始化输出
        
        res = {}
        res["input_args"] = {}
        res["input_args"]["product_detail"] = product_detail
        res["input_args"]["buyer_company_name"] = buyer_company_name
        res["input_args"]["buyer_tax_number"] = buyer_tax_number
        res["input_args"]["invoice_type"] = invoice_type
        res["input_args"]["remark"] = remark
        invoice_type_map = {"全电普通发票": "1", "全电专用发票": "2"}
        invoice_type_num = invoice_type_map.get(invoice_type, None)
        if invoice_type_num is None:
            res["status"] = "fail"
            res["results"] = f"发票种类<{invoice_type}>填错了，目前只支持'全电普通发票'和'全电专用发票'，请进行修改."
            return res
        itemlist = []
        invoice_amounts = 0 
        tax_amounts = 0 
        
       
        for product in product_detail:
            product = product.dict()
            product_total_amount = '{:.2f}'.format(product["money"]) 
            # tax_rate = product_tax_map.get(product["code"], None)
            tax_rate = 0.09 
            if tax_rate is None:
                res["status"] = "fail"
                res["results"] = f"您提供的商品<{product['name']}>的税收编码<{product['code']}>是错误的，请进行修改."
                return res
            product_amount = '{:.2f}'.format(float(product_total_amount) / (1 + tax_rate))
            tax_amount = '{:.2f}'.format(float(product_amount) * tax_rate)
            invoice_amounts += float(product_amount)
            tax_amounts += float(tax_amount)
            itemlist.append({
                "specModel": "",
                "zeroTaxRateFlag": "",
                "taxAmount": tax_amount,
                "taxRate": '{:.2f}'.format(tax_rate),
                "goodsCode": product["code"],
                "detailAmount": product_amount,
                "discountType": "0",
                "goodsName": product["name"],
                "preferentialPolicy": "0",
                "vatException": ""
            })
        # 创建invoice_info
        invoice_info = {
            "taxFlag": "0",
            "inventoryFlag": "0",
            "inventoryProjectName": "0",
            "salerAddress": seller_address,
            "salerPhone": seller_phone,
            "salerAccount": seller_account,
            "salerCardName": seller_cardname,
            "salerCardNumber": seller_cardnumber,
            "salerTaxNo": seller_tax_number,
            "buyerName": buyer_company_name,
            "buyerTaxNo": buyer_tax_number,
            "invoiceAmount": '{:.2f}'.format(invoice_amounts),
            "totalAmount": '{:.2f}'.format(invoice_amounts + tax_amounts),
            "totalTaxAmount": '{:.2f}'.format(tax_amounts),
            "type": "0",
            "reviewer": reviewer,
            "payee": payee,
            "originalInvoiceCode": "",
            "originalInvoiceNo": "",
            "invoiceType": invoice_type_num,
            "invoiceNo": "92698367",
            "invoiceCode": "050001901011",
            "serialNo": "9a8b0aa715314c327380"
        }

        file_path = create_pdf(invoice_info)
        
        result = {
                    "input_args": {
                        "product_detail":product_detail,
                        "buyer_company_name": buyer_company_name,
                        "buyer_tax_number": buyer_tax_number,
                        "invoice_type": invoice_type,
                        "remark": ""
                    },
                    "status": "success",
                    "results": {
                        "downloadUrl": f"s3://{bucket}/invoice.pdf",
                        "invoiceNo": "92698367",
                        "invoiceCode": "050001901011"
                    }
                }
        return result


    @staticmethod
    def send_invoice_email(invoice_code: str, invoice_number: str, email_address: str) -> dict:
        """This function send the issued invoice file link to a specified email address"""
        s3_file_path = f"s3://{bucket}/invoice.pdf"
        logger.debug(s3_file_path)
        result = send_eamil(email_address, s3_file_path)

        # 定义输出
        res = {}
        res["input_args"] = {}
        res["input_args"]["invoice_code"] = invoice_code
        res["input_args"]["invoice_number"] = invoice_number
        res["input_args"]["email_address"] = email_address
        if result["errcode"] == "0000":
            res["status"] = "success"
            res["results"] = "邮件发送成功"
        else:
            res["status"] = "fail"
            res["results"] = "邮件发送失败,请稍后尝试重新发送."
        return res
    
    @staticmethod
    def knowledge_base_retrieve(query: str) -> dict:
        """This function will retreive knowledge_base"""
        knowledge_base_id = KNOWLEDGEB_BASE_ID
        
        response = knowledgebases_client.retrieve(
            knowledgeBaseId=knowledge_base_id,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 1 
                }
            },
        )
        chunks = list(filter(lambda x: x["score"] > 0.7 ,response["retrievalResults"]))
        res ={}
        res["input_args"]={}
        res["input_args"]["query"] = query
        if len(chunks) != 0:
            res["status"] = "success"
            res["retrieved_documents"] = chunks
        else:
            res["status"] = "fail"
            res["retrieved_documents"] = []
        return res
            

