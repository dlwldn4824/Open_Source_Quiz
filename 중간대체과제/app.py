import time
import json
from pathlib import Path
import difflib
import re
import importlib

import streamlit as st
import streamlit.components.v1 as components

import quiz_data as quiz_module


st.set_page_config(page_title="2026 MZ 밈고사", page_icon="🧠", layout="centered")


STUDENT_ID = "2024404009"
STUDENT_NAME = "이지우"


_QUIZ_DATA_PATH = Path(__file__).parent / "quiz_data.py"


@st.cache_data
def load_quiz_data(quiz_data_mtime: float):
    # quiz_data.py가 수정되면 mtime이 바뀌어 캐시가 자동 무효화됩니다.
    importlib.reload(quiz_module)
    return quiz_module.quiz_data


def validate_username(username: str) -> list[str]:
    u = (username or "").strip()
    errors: list[str] = []
    if not u:
        return ["아이디를 입력해주세요."]
    if len(u) < 4 or len(u) > 16:
        errors.append("아이디 길이는 4~16자여야 합니다.")
    if not re.fullmatch(r"[A-Za-z0-9]+", u):
        errors.append("아이디는 영문/숫자만 사용할 수 있습니다.")
    if not re.search(r"[A-Za-z]", u) or not re.search(r"\d", u):
        errors.append("아이디는 영문과 숫자를 각각 1개 이상 포함해야 합니다.")
    return errors


def validate_password(password: str) -> list[str]:
    p = password or ""
    errors: list[str] = []
    if not p:
        return ["비밀번호를 입력해주세요."]
    if len(p) < 8 or len(p) > 32:
        errors.append("비밀번호 길이는 8~32자여야 합니다.")
    if not re.search(r"[A-Za-z]", p):
        errors.append("비밀번호는 영문을 1개 이상 포함해야 합니다.")
    if not re.search(r"\d", p):
        errors.append("비밀번호는 숫자를 1개 이상 포함해야 합니다.")
    if not re.search(r"[^A-Za-z0-9]", p):
        errors.append("비밀번호는 특수문자를 1개 이상 포함해야 합니다.")
    return errors


def check_login(username: str, password: str) -> bool:
    return (len(validate_username(username)) == 0) and (len(validate_password(password)) == 0)


def _norm_text(s: str) -> str:
    return "".join((s or "").strip().lower().split())


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


_BEST_RECORD_PATH = Path(__file__).parent / "best_record.json"


def _load_best_records() -> dict:
    try:
        if _BEST_RECORD_PATH.exists():
            return json.loads(_BEST_RECORD_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_best_records(records: dict) -> None:
    try:
        _BEST_RECORD_PATH.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _is_better_record(new: dict, old: dict | None) -> bool:
    if not old:
        return True
    if new["score"] != old.get("score"):
        return new["score"] > old.get("score")
    # tie-breaker: faster time wins
    return float(new["total_elapsed"]) < float(old.get("total_elapsed", float("inf")))


def get_time_bonus(seconds: float) -> int:
    if seconds <= 3:
        return 5
    if seconds <= 5:
        return 3
    if seconds <= 8:
        return 2
    return 0


def get_grade(correct_count: int, total_questions: int) -> tuple[str, str]:
    if total_questions <= 0:
        return "측정 불가", "문항 수가 0이라 등급을 계산할 수 없습니다."

    ratio = correct_count / total_questions
    if ratio >= 0.93:
        return "밈 인사이더", "시간과 상관없이 밈을 정확히 꿰고 있습니다."
    if ratio >= 0.79:
        return "상위 밈러", "대부분의 밈을 정확히 알고 있습니다."
    if ratio >= 0.64:
        return "적응형 사용자", "알긴 아는데 가끔 헷갈릴 때가 있습니다."
    if ratio >= 0.43:
        return "밈 눈치챙김 단계", "조금 더 스크롤이 필요합니다."
    return "인터넷 뉴비", "아직 2026 밈 생태계 적응이 덜 된 상태입니다."


def init_session():
    defaults = {
        "logged_in": False,
        "username": "",
        "nickname": "",
        "current_index": 0,
        "score": 0,
        "quiz_finished": False,
        "results": [],
        "question_start_time": None,
        "shown_hints": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_quiz():
    st.session_state.current_index = 0
    st.session_state.score = 0
    st.session_state.quiz_finished = False
    st.session_state.results = []
    st.session_state.question_start_time = None


def logout():
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.nickname = ""
    reset_quiz()


init_session()
questions = load_quiz_data(_QUIZ_DATA_PATH.stat().st_mtime)

st.title("2026 MZ 밈고사")
st.caption("이미지 기반 밈 퀴즈 + 시간 반영 점수 시스템")

st.write(f"학번: {STUDENT_ID}")
st.write(f"이름: {STUDENT_NAME}")

st.divider()

if not st.session_state.logged_in:
    st.subheader("로그인")
    st.write("로그인 후 퀴즈를 시작할 수 있습니다.")
    st.caption("퀴즈를 시작하면(첫 문제 화면부터) 각 문제 풀이 시간이 초 단위로 측정됩니다.")

    with st.form("login_form"):
        username = st.text_input("아이디")
        nickname = st.text_input("닉네임(랭킹 표시용)")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    st.info(
        "로그인 규칙\n"
        "- 아이디: 영문/숫자만, 4~16자, 영문+숫자 혼합\n"
        "- 비밀번호: 8~32자, 영문+숫자+특수문자 포함"
    )

    if submitted:
        u_errors = validate_username(username)
        p_errors = validate_password(password)
        n = (nickname or "").strip()
        n_errors: list[str] = []
        if not n:
            n_errors.append("닉네임을 입력해주세요.")
        elif len(n) > 12:
            n_errors.append("닉네임은 12자 이하로 입력해주세요.")

        if u_errors or p_errors or n_errors:
            if u_errors:
                st.error("아이디 조건이 맞지 않습니다:\n- " + "\n- ".join(u_errors))
            if p_errors:
                st.error("비밀번호 조건이 맞지 않습니다:\n- " + "\n- ".join(p_errors))
            if n_errors:
                st.error("닉네임 조건이 맞지 않습니다:\n- " + "\n- ".join(n_errors))
        elif check_login(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.nickname = n
            reset_quiz()
            st.success("로그인 성공")
            st.rerun()
        else:
            st.error("로그인 실패: 아이디 또는 비밀번호를 확인하세요.")

else:
    display_name = st.session_state.nickname or st.session_state.username
    st.sidebar.write(f"로그인 사용자: {display_name}")
    with st.sidebar.expander("랭킹 보기"):
        records = _load_best_records()
        if not records:
            st.caption("아직 저장된 최고 기록이 없습니다.")
        else:
            rows = []
            for user, rec in records.items():
                nick = rec.get("nickname") or user
                rows.append(
                    {
                        "user": user,
                        "nickname": nick,
                        "score": int(rec.get("score", 0)),
                        "correct": f"{int(rec.get('correct_count', 0))}/{int(rec.get('total_questions', 0))}",
                        "time_sec": float(rec.get("total_elapsed", 0.0)),
                    }
                )
            rows.sort(key=lambda r: (-r["score"], r["time_sec"], r["nickname"]))
            for rank, r in enumerate(rows, start=1):
                st.write(f"**{rank}위**  {r['nickname']}  ·  {r['score']}점  ·  {r['correct']}  ·  {r['time_sec']:.2f}초")

    if st.sidebar.button("로그아웃"):
        logout()
        st.rerun()

    if st.session_state.quiz_finished:
        total = st.session_state.score
        total_questions = len(questions)
        correct_count = sum(1 for r in st.session_state.results if r.get("is_correct"))
        total_elapsed = sum(float(r.get("elapsed", 0.0)) for r in st.session_state.results)
        grade, comment = get_grade(correct_count, total_questions)
        record = {
            "score": int(total),
            "correct_count": int(correct_count),
            "total_questions": int(total_questions),
            "total_elapsed": float(total_elapsed),
            "nickname": st.session_state.nickname or st.session_state.username,
        }
        username = st.session_state.username or "anonymous"
        best_records = _load_best_records()
        prev_best = best_records.get(username)
        is_new_best = _is_better_record(record, prev_best)
        if is_new_best:
            best_records[username] = record
            _save_best_records(best_records)
        best_for_user = best_records.get(username, record)

        st.subheader("최종 결과")
        st.success(f"총점: {total}점")
        st.write(f"맞춘 문제: **{correct_count} / {total_questions}**")
        st.write(f"총 소요 시간: **{total_elapsed:.2f}초**")
        st.write(f"등급: **{grade}**")
        st.write(comment)
        st.divider()
        st.subheader("내 최고 기록")
        if is_new_best:
            st.success("최고 기록 갱신!")
        st.write(f"최고 점수: **{best_for_user['score']}점**")
        st.write(f"맞춘 문제: **{best_for_user['correct_count']} / {best_for_user['total_questions']}**")
        st.write(f"총 소요 시간: **{best_for_user['total_elapsed']:.2f}초**")

        st.write("점수 계산 방식")
        st.write("- 정답 점수: 10점")
        st.write("- 시간 보너스: 3초 이내 +5 / 5초 이내 +3 / 8초 이내 +2")

        st.divider()
        st.subheader("문항별 결과")

        for idx, result in enumerate(st.session_state.results, start=1):
            status = "정답" if result["is_correct"] else "오답"
            st.markdown(
                f"""
**{idx}. {result['question']}**  
- 선택한 답: {result['selected_option']}  
- 정답: {result['correct_option']}  
- 소요 시간: {result['elapsed']:.2f}초  
- 획득 점수: {result['earned_score']}점  
- 결과: {status}
"""
            )
            st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("다시 풀기"):
                reset_quiz()
                st.rerun()
        with col2:
            if st.button("처음으로"):
                logout()
                st.rerun()

    else:
        total_questions = len(questions)
        current_index = st.session_state.current_index
        current_question = questions[current_index]
        q_type = current_question.get("type", "choice")

        st.subheader("퀴즈 진행 중")
        st.write(f"{current_index + 1} / {total_questions} 문제")
        st.progress((current_index + 1) / total_questions)

        if st.session_state.question_start_time is None:
            st.session_state.question_start_time = time.time()

        image_path = f"images/{current_question['image']}"
        st.image(image_path, use_container_width=True)

        st.markdown(f"### 문제 {current_question['id']}")
        st.write(current_question["question"])

        hint = current_question.get("hint")
        if hint:
            hint_key = str(current_question.get("id"))
            if st.button("힌트 보기", key=f"hint_btn_{hint_key}"):
                st.session_state.shown_hints[hint_key] = True
            if st.session_state.shown_hints.get(hint_key):
                st.info(hint)

        widget_key = f"question_{current_question['id']}"
        if q_type == "text":
            # 주관식: 엔터로 제출되도록 form 사용
            with st.form(f"answer_form_{current_question['id']}", clear_on_submit=False):
                user_text = st.text_input("정답을 입력하세요.", key=widget_key)

                # Streamlit은 text_input autofocus를 기본 지원하지 않아 JS로 포커스를 잡습니다.
                # 마지막 텍스트 입력창을 대상으로 여러 번 재시도합니다.
                components.html(
                    """
<script>
(() => {
  const focusCurrentFormTextInput = () => {
    try {
      // Streamlit form은 <form> 태그로 렌더링됩니다.
      // 현재 문제는 "가장 마지막 form"으로 간주하고 그 안의 text input에 포커스합니다.
      const forms = Array.from(parent.document.querySelectorAll('form'));
      const form = forms[forms.length - 1];
      if (!form) return false;

      const target = form.querySelector('input[type="text"]');
      if (target) {
        target.focus();
        target.select?.();
        return true;
      }
    } catch (e) {}
    return false;
  };

  let tries = 0;
  const tick = () => {
    tries += 1;
    if (focusCurrentFormTextInput()) return;
    if (tries < 20) setTimeout(tick, 80);
  };
  setTimeout(tick, 30);
})();
</script>
                    """,
                    height=0,
                )

                submitted = st.form_submit_button("제출")

            choice = user_text
        else:
            choice = st.radio("정답을 선택하세요.", current_question["options"], key=widget_key)

        if (q_type == "text" and submitted) or (q_type != "text" and st.button("제출")):
            elapsed = time.time() - st.session_state.question_start_time
            if q_type == "text":
                norm_choice = _norm_text(choice)
                accepted = {_norm_text(a) for a in current_question.get("answers", [])}
                if current_question.get("fuzzy"):
                    min_sim = float(current_question.get("min_similarity", 0.86))
                    best_sim = 0.0
                    best_match = ""
                    for a in accepted:
                        sim = _similarity(norm_choice, a)
                        if sim > best_sim:
                            best_sim = sim
                            best_match = a
                    is_correct = (norm_choice in accepted) or (best_sim >= min_sim)
                else:
                    is_correct = norm_choice in accepted
                correct_option = ", ".join(current_question.get("answers", []))
            else:
                selected_index = current_question["options"].index(choice)
                is_correct = selected_index == current_question["answer"]
                correct_option = current_question["options"][current_question["answer"]]

            earned_score = 0
            if is_correct:
                earned_score = 10 + get_time_bonus(elapsed)

            st.session_state.score += earned_score
            st.session_state.results.append(
                {
                    "question": current_question["question"],
                    "selected_option": choice,
                    "correct_option": correct_option,
                    "elapsed": elapsed,
                    "earned_score": earned_score,
                    "is_correct": is_correct,
                }
            )

            st.session_state.current_index += 1
            st.session_state.question_start_time = None

            if st.session_state.current_index >= total_questions:
                st.session_state.quiz_finished = True

            st.rerun()

