import re

import numpy as np
import streamlit as st


st.set_page_config(page_title="성적 관리 + 등수 계산기", page_icon="📊", layout="centered")

st.title("성적 관리 + 등수 계산기")
st.write(
    "중간/기말/과제/출석 점수로 총점을 계산하고, 전체 점수 분포에서 내 등수를 확인할 수 있습니다."
)

subject = st.selectbox(
    "과목 선택 (선택 기능)",
    ["(선택 안 함)", "오픈소스소프트웨어", "자료구조", "운영체제", "기타"],
)

st.divider()
st.header("1) 총점 계산기")

defaults = st.session_state.get(
    "scores",
    {"mid": 0, "final": 0, "assignment": 0, "attendance": 0, "wmid": 30, "wfinal": 40, "wassignment": 20, "wattendance": 10},
)

col1, col2 = st.columns(2)
with col1:
    mid = st.numberinput("중간고사 점수", 0, 100, int(defaults["mid"]))
    assignment = st.numberinput("과제 점수", 0, 100, int(defaults["assignment"]))
with col2:
    final = st.numberinput("기말고사 점수", 0, 100, int(defaults["final"]))
    attendance = st.numberinput("출석 점수", 0, 20, int(defaults["attendance"]))

st.subheader("가중치 설정 (%)")
wmid = st.slider("중간 비중", 0, 100, int(defaults["wmid"]))
wfinal = st.slider("기말 비중", 0, 100, int(defaults["wfinal"]))
wassignment = st.slider("과제 비중", 0, 100, int(defaults["wassignment"]))
wattendance = st.slider("출석 비중", 0, 100, int(defaults["wattendance"]))

weight_sum = wmid + wfinal + wassignment + wattendance
if weight_sum != 100:
    st.error(f"가중치의 합은 반드시 100이어야 합니다. (현재 합: {weight_sum})")

if st.button("총점 계산", type="primary"):
    if weight_sum == 100:
        total = (
            mid * (wmid / 100)
            + final * (wfinal / 100)
            + assignment * (wassignment / 100)
            + attendance * (wattendance / 100)
        )
        st.success(f"총점: {total:.2f}점")
        st.session_state["last_total"] = float(total)
        st.session_state["scores"] = {
            "mid": mid,
            "final": final,
            "assignment": assignment,
            "attendance": attendance,
            "wmid": wmid,
            "wfinal": wfinal,
            "wassignment": wassignment,
            "wattendance": wattendance,
        }
        if subject != "(선택 안 함)":
            st.caption(f"과목: {subject}")

st.divider()
st.header("2) 전체 분포 기반 등수 계산")

prefill_total = float(st.session_state.get("last_total", 0.0))
myscore = st.numberinput("내 총점", 0.0, 200.0, prefill_total, step=0.1)
scorestext = st.textarea(
    "전체 학생 점수 목록 (쉼표/공백/줄바꿈 모두 가능)\n예: 88, 74, 90, 62",
    height=120,
)


def parse_scores(text: str) -> np.ndarray:
    tokens = [t for t in re.split(r"[,\s]+", text.strip()) if t]
    scores = [float(t) for t in tokens]
    return np.array(scores, dtype=float)


if st.button("등수 계산"):
    try:
        scorearray = parse_scores(scorestext)
        if scorearray.size == 0:
            st.error("점수 목록이 비어 있습니다. 예: 80, 92, 77, 65")
        else:
            higher = int(np.sum(scorearray > myscore))
            rank = higher + 1
            n = int(scorearray.size)
            top_percent = (rank - 1) / n * 100  # 상위 x% (작을수록 좋음)
            st.subheader("등수 결과")
            st.write(f"총 {n}명 기준으로 **{rank}등** 입니다.")
            st.write(f"상위 비율: **{top_percent:.2f}%**")

            hist, bin_edges = np.histogram(scorearray, bins="auto")
            st.caption("점수 분포 (히스토그램)")
            st.bar_chart(
                {"count": hist},
                x=bin_edges[:-1],
            )
    except ValueError:
        st.error("점수 목록 형식이 잘못되었습니다. 예: 80, 92, 77, 65")
