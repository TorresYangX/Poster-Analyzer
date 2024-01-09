import json, requests
from paddleocr import PaddleOCR, draw_ocr
from matplotlib import pyplot as plt
from tqdm import tqdm


ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # need to run only once to download and load model into memory
# Define the body of the request
system_content = """
#### 以下是需要从宣传海报文本中提取的信息，括号内为提示信息，指示应该提取什么：
报告人：
报告人单位(报告人来自哪个学校、机构、企业):
讲座组织部门:
讲座系列名称：
期号:
国家/地区(中华人民共和国、美国、澳大利亚等):
语言(如果文本中有主讲语言，则直接使用；如果没有，则根据文本的语言或报告人信息猜测。可选项：(中文、英文)):
关键词(3-5个):
摘要(如果文本主要为中文,则摘要200-400字左右;如果文本主要为英文,则摘要200 words左右):
"""

def askModel(user_content, Model):
    if Model == "GPT":
        url = "https://api.openai-sb.com/v1/chat/completions"

        # Define the headers
        headers = {
            "Authorization": "Bearer sb-8a0ab39947ff64ab0ef3ab0363e898a949550364acb522aa",
            "Content-Type": "application/json",
        }


        data = {
            "model": "gpt-3.5-turbo",
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": system_content
                },
                {
                    "role": "user",
                    "content": user_content
                },

            ],
            "max_tokens": 2048
        }

        # Make the POST request
        response = requests.post(url, headers=headers, json=data).json()
        return response["choices"][0]["message"]["content"]

    else:
        access_token = '24.38096547b3169ae031dc39dba9e77270.2592000.1705153660.282335-44976318'
        url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token=" + access_token
        payload = json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": "你好"
                }
                ,
                {
                "role": "assistant",
                "content": system_content
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("POST", url, headers=headers, data=payload).json()
        return response["result"]




#通过海报的唯一标识码读取海报信息
import get_info
import pandas as pd
import tqdm
from PIL import Image
from io import BytesIO
def readPosterByUniqueCode(id):
    info=get_info.get_info(id)
    if info.get("poster") is None:
        return None,0
    r = requests.get(url=info["poster"])
    if r.status_code == 200:
        image_bytes_io = BytesIO(r.content)
        image = Image.open(image_bytes_io)
        # 获取BytesIO缓冲区的大小，即图像数据的大小
        image_size_bytes = image_bytes_io.getbuffer().nbytes
        # 将字节转换为千字节
        size = image_size_bytes / 1024
        image = image.convert("RGB")
        image.save("image.jpg", "JPEG")
    img_path = 'image.jpg'
    result = ocr.ocr(img_path, cls=True)
    content = ""
    for idx in range(len(result)):
        res = result[idx]
        for line in res:
            content += line[-1][0] + "\n"
    return content, size

##path:需要更新的EXCEL文件
##start:起始页码 end:终止页码
def update(path,Model,M=10,start=1,end=10):
    df = pd.read_excel(path)
    id_list = get_info.get_id_list(start,end)
    # 把所有不在df的id列中但是在id_list列中的id取出来
    ids_to_add = set(id_list) - set(df['id'])
    print(ids_to_add)
    try:
        data_to_append = []
        for id in tqdm.tqdm(ids_to_add):
            info=get_info.get_info(id)
            content, size=readPosterByUniqueCode(id)
            if content is None:
                response=None
            else:
                response=askModel(content, Model)
            dict = {}
            dict["id"] = info["id"]
            dict["讲座名称"] = info["title"]
            dict["海报内容"] = content
            # change the format of time, info["time"] is like "2023年12月29日 16:20", I need 2023/12/29
            dict["讲座时间"] = info["time"][0:4] + "/" + info["time"][5:7] + "/" + info["time"][8:10]
            dict["讲座地点"] = info["location"]
            dict["海报文件大小"] = f'{size:.2f} KB'
            if response is not None:
                dict["路径url"] = info["poster"]
                lines = response.split("\n")
                for line in lines:
                    parts=line.split("：",1)
                    if len(parts) == 2:
                        dict[parts[0]] = parts[1]
            if dict["讲座时间"] is not None:
                dict["年份"]=dict["讲座时间"][0:4]
            else:
                dict["年份"]="2023"
            data_to_append.append(dict)
            # print(dict)
            #TODO:每十次循环将dict加入到上面路径的EXCEL表格中
            if len(data_to_append)%M==0:
                df=pd.read_excel(path)
                df_append=pd.DataFrame(data_to_append)
                # Use the ExcelWriter, specifying the workbook as a parameter
                merge_columns = ["id", "路径url", "讲座名称", "海报内容", "讲座时间", "讲座地点", "海报文件大小",
                                 "报告人",
                                 "报告人单位", "讲座组织部门", "讲座系列名称", "期号", "国家/地区", "语言", "关键词",
                                 "摘要", "年份"]
                merged_file = pd.concat([df,df_append], ignore_index=True)
                merged_file=merged_file[merge_columns]
                merged_file.to_excel(path, index=False)
                data_to_append = []
        df = pd.read_excel(path)
        df_append = pd.DataFrame(data_to_append)
        # Use the ExcelWriter, specifying the workbook as a parameter
        merge_columns = ["id", "路径url", "讲座名称", "海报内容", "讲座时间", "讲座地点", "海报文件大小",
                         "报告人",
                         "报告人单位", "讲座组织部门", "讲座系列名称", "期号", "国家/地区", "语言", "关键词",
                         "摘要", "年份"]
        merged_file = pd.concat([df, df_append], ignore_index=True)
        merged_file = merged_file[merge_columns]
        merged_file.to_excel(path, index=False)
        data_to_append = []
    except Exception as e:
        print("An error occurred:", str(e))


# update("result3.xlsx","WenXinYiYan",10,1,50)
#%%
