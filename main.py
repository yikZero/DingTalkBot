import socket
import os
import requests
import json
import time
import copy
from dingtalkchatbot.chatbot import DingtalkChatbot

# 钉钉推送信息
dingPush_Switch = True #钉钉推送开关
webhook = os.environ["DINGTALKBOT_WEBHOOK"]
secret = os.environ["DINGTALKBOT_SECRET"]
username = os.environ["USERNAME_ZF"]
password = os.environ["SECRET_ZF"]

def messagePush(text):
    if dingPush_Switch:
        # 初始化机器人
        FlyBot = DingtalkChatbot(webhook, secret=secret)
        at_mobiles = os.environ["PHONENUMBER"]
        FlyBot.send_text(msg=text, at_mobiles=str(at_mobiles))

def get_gpa(msg):
    gp = 0
    credit = 0
    for item in msg:
        if item[6] != "任选课":
            gp = gp + item[4] * item[5]
            credit = credit + item[4]
    if credit != 0:
        return round(gp / credit, 4)
    else:
        return 0


def beautify_msg(msg):
    for item in msg:
        item[1] = "{0}({1}%)".format(item[1], 100 - item[7])
        item[2] = "{0}({1}%)".format(item[2], item[7])
    return msg


def get_msg(title,msg):
    rows = []
    for score in beautify_msg(msg):
        row = "- {0}：{1}".format(score[0], score[3]) +'\n'
        rows.append(row)
    gpa = get_gpa(msg)
    total_text = title +'\n\n' +'-----------------------\n' #数据整理输出
    for row in rows:
        total_text = total_text + row
    total_text = total_text + '-----------------------\n' + '- GPA：' +str(gpa)
    return total_text


def error(msg):
    print(msg)


def get_json(url):
    headers = {
        "Host": "api.jh.zjut.edu.cn",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/79.0.3945.88 Safari/537.36 Edg/79.0.309.54 "
    }

    content = requests.get(url, headers=headers).content.decode().encode("GBK")
    result = json.loads(content)
    while result["status"] != "success":
        error('查询错误')
        time.sleep(1)
        content = requests.get(url, headers=headers).content.decode().encode("GBK")
        result = json.loads(content)
    return result


def get_score_detail(cfg):  # 返回成绩信息的res
    url = "http://api.jh.zjut.edu.cn/student/scoresDetailZf.php?ip=164&username="+ username + "&password="+ password+"&year={0}&term={1}". \
        format(cfg[0], cfg[1])
    score_detail = get_json(url)
    score_summary = {}
    value = {}
    for each in score_detail["msg"]:
        if not (score_summary.__contains__(each['kcmc'])):
            value.clear()
        value[each['xmblmc']] = each['成绩']
        score_summary[each['kcmc']] = copy.deepcopy(value)
    score_list = []
    for k in score_summary.items():
        score_item = [0, 0, 0, 0, 0, 0, 0, 0]  # 课程名称，平时成绩，期末成绩，总评，学分，学分绩点，是否计入,期末考占比
        score_item[0] = k[0]
        for score in k[1].items():
            if "平时" in score[0]:
                score_item[1] = score[1]
            if "期末" in score[0]:
                score_item[2] = score[1]
                score_item[7] = eval(score[0].split("(")[1].split("%")[0])
            if "总评" in score[0]:
                score_item[3] = score[1]
        score_list.append(score_item)
    return score_list


def get_gpa_info(cfg, res):  # 为res添加GPA信息
    url = "http://api.jh.zjut.edu.cn/student/scoresZf.php?ip=164&username="+ username + "&password="+ password+"&year={0}&term={1}". \
        format(cfg[0], cfg[1])
    score_detail = get_json(url)
    for score in score_detail["msg"]:
        for item in res:
            if item[0] == score["kcmc"]:
                item[4] = eval(score["xf"])
                item[5] = eval(score["jd"])
                item[6] = score["kcxzmc"]
    return res


def check_password(cfg):  # 判断密码是否正确，正确返回True
    return True  # TODO 实现功能


def get_config():
    config_file = open('config.ini', mode='r', encoding='utf-8')
    return config_file.read().split('\n')


if __name__ == '__main__':
    config = get_config()
    if not check_password(config):
        error("密码错误")
        exit(0)
    score_list = get_score_detail(config)
    scores = get_gpa_info(config, score_list)  # 加上GPA信息
    messagePush(get_msg('成绩统计：',scores))
    size = len(score_list)  # 获取初始数据
    while True:
        try:
            new_score_list = get_score_detail(config)
            if len(new_score_list) != size:  # 出新成绩了
                scores = get_gpa_info(config, new_score_list)  # 加上GPA信息
                messagePush(get_msg('出新成绩啦！',scores))
        except requests.exceptions.ConnectionError as e:
            error('Network Error')
        except KeyError as e:
            error('KeyError')
        except json.decoder.JSONDecodeError as e:
            error('JsonDecodeError')
        except Exception as e:
            error('error')
        finally:
            time.sleep(60)
