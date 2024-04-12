
from src.tools.functions import UsefullFunctions,InvoiceInput,SendInvoiceEmailInput,RetrieveKnowledgeBaseInput

from pydantic import BaseModel
from typing import Dict,List, Type
from langchain.tools import BaseTool
import logging
import sys

logger = logging.getLogger(__name__)

def str_to_class(classname):
    return getattr(sys.modules["src.tools.functions"], classname)

# class InvoiceImageGenTool(MyBaseTool):
class InvoiceImageGenTool(BaseTool):
    name = "generate_preview_invoice_info"
    description = "Generate a temporary preview invoice info."
    # args_schema = InvoiceInput
    args_schema: Type[BaseModel] = InvoiceInput
    def _run(self, product_detail: str,
             buyer_company_name: str,
             buyer_tax_number: str,
             invoice_type: str= "全电普通发票",
             remark: str = ""):
        if isinstance(product_detail, str):
            product_detail = eval(product_detail)
        return UsefullFunctions.generate_preview_invoice_info(user_id="000001",
                                                              product_detail=product_detail,
                                                              buyer_company_name=buyer_company_name,
                                                              buyer_tax_number=buyer_tax_number,
                                                              invoice_type=invoice_type,
                                                              remark=remark)
    def _arun(self, product_detail: List[Dict],
             buyer_company_name: str,
             buyer_tax_number: str,
             invoice_type: str= "全电普通发票",
             remark: str = ""):
        raise NotImplementedError("This tool does not support async")

# class InvoiceIssueTool(MyBaseTool):
class InvoiceIssueTool(BaseTool):
    name = "issue_invoice"
    description = "Issue invoice file formally."
    # args_schema = InvoiceInput
    args_schema: Type[BaseModel] = InvoiceInput
    def _run(self, product_detail: str,
             buyer_company_name: str,
             buyer_tax_number: str,
             invoice_type: str= "全电普通发票",
             remark: str = ""):
        if isinstance(product_detail, str):
            product_detail = eval(product_detail)
        return UsefullFunctions.issue_invoice(user_id="000001",
                                             product_detail=product_detail,
                                             buyer_company_name=buyer_company_name,
                                             buyer_tax_number=buyer_tax_number,
                                             invoice_type=invoice_type,
                                             remark=remark)
    def _arun(self, product_detail: List[Dict],
             buyer_company_name: str,
             buyer_tax_number: str,
             invoice_type: str= "全电普通发票",
             remark: str = ""):
        raise NotImplementedError("This tool does not support async")

# class SendInvoiceEmailTool(MyBaseTool):
class SendInvoiceEmailTool(BaseTool):
    name = "send_email"
    description = "Send the issued invoice file to user's email address. When asked to send an email during our conversation, you should call this function with the appropriate arguments to simulate sending the email."
    # description = "Send the issued invoice file to user's email address."
    # description = "After issueed invoice file, send the issued invoice file to a specified email address."
    args_schema: Type[BaseModel] = SendInvoiceEmailInput
    def _run(self, invoice_code:str, invoice_number: str, email_address: str):
        return UsefullFunctions.send_invoice_email(invoice_code, invoice_number, email_address)
    def _arun(self, invoice_code:str, invoice_number: str, email_address: str):
        raise NotImplementedError("This tool does not support async")

class RetrieveKnowledgeBaseTool(BaseTool):
    name = "knowledge_base_retrieve"
    description = "An Knowledge Base for china invoice policy."
    args_schema: Type[BaseModel] = RetrieveKnowledgeBaseInput

    def _run(self, query: str):
        return UsefullFunctions.knowledge_base_retrieve(query)
    def _arun(self, query: str):
        raise NotImplementedError("This tool does not support async")

def construct_format_parameters_prompt(parameters):
    constructed_prompt = "\n".join(f"<parameter>\n<name>{parameter['name']}</name>\n<type>{parameter['type']}</type>\n<description>{parameter['description']}</description>\n</parameter>" for parameter in parameters)

    return constructed_prompt


tools_list = [
    InvoiceImageGenTool(),
    InvoiceIssueTool(),
    SendInvoiceEmailTool(),
    RetrieveKnowledgeBaseTool()
]
tools_name = [tool.name for tool in tools_list]

def construct_format_tool_for_claude_prompt(tools_list):
    tool_strings = []
#     PARAM_STRING = """<description>{description}</description>
# <examples>{examples}</examples>
# <type>{type}</type>
# """
    PARAM_STRING = """<description>{description}</description>
<type>{type}</type>
"""
    ITEM_STRING = """<items>
<item_name>{name}</item_name>
<item_description>{description}</item_description>
<item_type>{type}</item_type>
</items>
"""
    for tool in tools_list:
        parameters_string = ""
        for tool_arg, values in tool.args.items():
            logger.debug(tool_arg)
            logger.debug(values) 
            if "default" in values:
                continue
            else:
                parameters_string += f"<parameter>\n<name>{tool_arg}</name>\n"
                if "type" in values:
                    parameters_string += PARAM_STRING.format(description=values['description'], type=values['type'])
                elif "allOf" in values:
                    ref_string = values['allOf'][0]['$ref'].split("/")[-1]
                    ref_class_params = str_to_class(ref_string).__fields__
                    logger.debug(ref_class_params)
                    for item_name, item_values in ref_class_params.items():
                        parameters_string += ITEM_STRING.format(name=item_name, description=item_values.description, type=item_values.annotation)

                if "items" in values:
                    ref_string = values['items']['$ref'].split("/")[-1]
                    ref_class_params = str_to_class(ref_string).__fields__
                    logger.debug(ref_class_params)
                    for item_name, item_values in ref_class_params.items():

                        parameters_string += ITEM_STRING.format(name=item_name, description=item_values.description, type=item_values.annotation)

            parameters_string += f"</parameter>\n"

        tool_strings.append(
            f"<tool_name>{tool.name}</tool_name>\n"
            "<description>\n"
            f"{tool.description}\n"
            "</description>\n"
            "<parameters>\n"
            f"{parameters_string}"
            "</parameters>\n"
            )
        
        tool_final_string =  "\n".join(tool_strings)
        logger.debug(tool_final_string)
    return tool_final_string

if __name__ == "__main__":
    print(construct_format_tool_for_claude_prompt(tools_list))