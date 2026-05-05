# 성적 관리 + 등수 계산 Streamlit 앱

중간/기말/과제/출석 점수로 **총점 계산**을 하고, 전체 점수 분포에서 **등수/상위 비율**을 확인하는 Streamlit 앱입니다.

## 구성

- `app.py`: Streamlit 앱
- `requirements.txt`: 실행 의존성

## 실행 방법

```bash
cd 실습3/grade-calculator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## EC2에서 실행 (제출용 예시)

```bash
streamlit run app.py --server.port 8080 --server.address 0.0.0.0
```

접속: `http://<EC2-IP>:8080`
