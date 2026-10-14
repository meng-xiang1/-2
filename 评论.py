import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header

import markdown
import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key=st.secrets["DEEPSEEK_KEY"],
    base_url="https://api.deepseek.com"
)

st.set_page_config(page_title="AI 评论分析", page_icon="📊")
st.title("📊 AI 评论分析")
st.caption("把评论粘进来,几分钟出一份分析报告")

with st.sidebar:
    st.header("📁 导入评论")
    上传 = st.file_uploader("上传评论(txt / csv)", type=["txt", "csv"])
    店铺名 = st.text_input("店铺或产品名(可选)")
    收件人 = st.text_input("报告发到哪个邮箱?(可选)")

if "评论" not in st.session_state:
    st.session_state.评论 = ""

if 上传 is not None:
    原始 = 上传.read()
    try:
        st.session_state.评论 = 原始.decode("utf-8")
    except UnicodeDecodeError:
        st.session_state.评论 = 原始.decode("gbk", errors="ignore")
    st.success("已导入:" + 上传.name)

评论 = st.text_area("或者把评论粘贴到这里(每条一行)",
                    value=st.session_state.评论, height=200)

提示 = """你是资深的电商数据分析师。下面是一批客户评论(店铺:""" + (店铺名 or "未填写") + """)。
请分析并输出一份报告。

【输出格式】(严格遵守,用 Markdown)
## 一、整体概况
- 评论总数:X 条
- 好评 / 中评 / 差评:X / X / X
- 一句话总结:客户最满意什么、最不满什么

## 二、差评原因分类
每类写:原因 + 条数 + 占比 + 1~2 条典型原话

## 三、最该立刻改的 3 个问题
每条给:问题(占比)→ 具体建议

## 四、做得好的地方

## 五、可直接用的补救话术

【规则】
- 只根据评论内容分析,不许编造
- 条数和占比要真实统计,不许估算
- 结论要具体、可执行,不许说空话
- 涉及给优惠券、给补偿、退款金额的,不要写死数字,
  用【待定】标出来让老板自己填

【评论内容】
""" + 评论

if st.button("开始分析", type="primary") and 评论.strip():
    with st.spinner("正在分析评论,请稍等..."):
        try:
            回复 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": 提示}]
            )
            st.session_state.报告 = 回复.choices[0].message.content
        except Exception as e:
            st.warning("出了点小问题,请稍后再试")
            print("出错了:", e)

if st.session_state.get("报告"):
    报告 = st.session_state.报告
    st.divider()
    st.markdown(报告)
    st.download_button("📥 下载报告", 报告, file_name="评论分析报告.md")

    st.divider()
    st.subheader("📧 发到客户邮箱")
    if st.button("发送报告") and 收件人:
        try:
            正文 = markdown.markdown(报告)
            正文 = ('<div style="font-family:-apple-system,\'PingFang SC\',sans-serif;'
                    'font-size:15px;line-height:1.8;color:#333;max-width:640px;">'
                    + 正文 + '</div>')
            msg = MIMEText(正文, "html", "utf-8")
            msg["Subject"] = Header("评论分析报告 " + str(datetime.date.today()), "utf-8")
            msg["From"] = st.secrets["SMTP_USER"]
            msg["To"] = 收件人

            s = smtplib.SMTP_SSL("smtp.qq.com", 465)
            s.login(st.secrets["SMTP_USER"], st.secrets["SMTP_CODE"])
            s.sendmail(st.secrets["SMTP_USER"], [收件人], msg.as_string())
            s.close()
            st.success("已发送到 " + 收件人)
        except Exception as e:
            st.error("发送失败,请检查邮箱配置")
            print("发信出错:", e)