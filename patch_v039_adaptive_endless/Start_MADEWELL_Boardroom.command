#!/bin/zsh
cd "$(dirname "$0")" || {
  echo "보드룸 폴더를 찾을 수 없습니다."
  read -n 1 -s -r "?아무 키나 누르면 종료됩니다."
  exit 1
}
cp ~/.env .env 2>/dev/null
python3 -m streamlit run app.py
