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
st.caption("把评论粘进来,自动生成报告并发到指定邮箱")

with st.sidebar:
    st.header("📁 导入评论")
    上传 = st.file_uploader("上传评论(txt / csv)", type=["txt", "csv"])
    店铺名 = st.text_input("店铺或产品名(可选)")

    st.divider()
    st.subheader("📧 报告发到哪个邮箱")

    # 从网址里读上次填的邮箱
    默认邮箱 = st.query_params.get("email", "")

    def 记住邮箱():
        值 = (st.session_state.get("邮箱框") or "").strip()
        if 值:
            st.query_params["email"] = 值      # 写进网址
        elif "email" in st.query_params:
            del st.query_params["email"]

    st.text_input("填一次,以后自动记住", value=默认邮箱,
                  key="邮箱框", on_change=记住邮箱)

    收件人 = (st.session_state.get("邮箱框") or 默认邮箱 or "").strip()
    if 收件人:
        st.caption("✅ 报告将发送到:" + 收件人)

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
【重要:同一商品的合并分析】
评论里可能带着多个链接/规格的标记(比如【链接A】【链接B】)。
如果它们其实卖的是"同一个商品",请把它们**合并起来**,
按"这个商品整体"来统计和分析,不要分开算。

判断依据:商品名称、材质、款式、评价里描述的实物特征。
如果明显是不同商品,再分开分析。

并且在报告开头注明:本次合并了 X 个链接、共 X 条评论。
- 只根据评论内容分析,不许编造
- 条数和占比要真实统计,不许估算
- 结论要具体、可执行,不许说空话
- 涉及给优惠券、给补偿、退款金额的,不要写死数字,
  用【待定】标出来让老板自己填

【评论内容】
""" + 评论

if st.button("开始分析并发送", type="primary") and 评论.strip():

    报告 = None
    with st.spinner("正在分析评论,请稍等..."):
        try:
            回复 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": 提示}]
            )
            报告 = 回复.choices[0].message.content
            st.session_state.报告 = 报告
            st.session_state.发送状态 = ""
        except Exception as e:
            st.error("分析失败,请稍后再试")
            print("分析出错:", e)

    if 报告:
        if not 收件人:
            st.session_state.发送状态 = "⚠️ 报告已生成,但还没配置收件邮箱"
        else:
            with st.spinner("正在发送邮件..."):
                try:
                    正文 = markdown.markdown(报告)
                    正文 = ('<div style="font-family:-apple-system,\'PingFang SC\','
                            '\'Microsoft YaHei\',sans-serif;font-size:15px;'
                            'line-height:1.8;color:#333333;max-width:640px;">'
                            + 正文 + '</div>')
                    msg = MIMEText(正文, "html", "utf-8")
                    msg["Subject"] = Header(
                        "评论分析报告 " + str(datetime.date.today()), "utf-8")
                    msg["From"] = st.secrets["SMTP_USER"]
                    msg["To"] = 收件人

                    s = smtplib.SMTP_SSL("smtp.qq.com", 465)
                    s.login(st.secrets["SMTP_USER"], st.secrets["SMTP_CODE"])
                    s.sendmail(st.secrets["SMTP_USER"], [收件人], msg.as_string())
                    s.close()

                    st.session_state.发送状态 = "✅ 报告已生成,并发到 " + 收件人
                except Exception as e:
                    st.session_state.发送状态 = "⚠️ 邮件没发出去:" + str(e)
                    print("发信出错:", e)

if st.session_state.get("报告"):
    st.divider()
    st.markdown(st.session_state.报告)
    st.download_button("📥 下载报告", st.session_state.报告,
                       file_name="评论分析报告.md")

if st.session_state.get("发送状态"):
    st.info(st.session_state.发送状态)
