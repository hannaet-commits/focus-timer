# 집중 타이머

Windows용 원형 집중 타이머입니다. 설치 없이 실행 파일을 받아 쓸 수 있고, 소스로도 실행할 수 있습니다.

## 실행 파일

[Releases](https://github.com/hannaet-commits/focus-timer/releases)에서 `FocusTimer.exe`를 받거나, 이 저장소의 `dist/FocusTimer.exe`를 받아 두 번 클릭합니다.

Windows가 게시자를 확인하지 못했다고 나오면 **추가 정보**를 누른 뒤 **실행**을 선택하면 됩니다. 서명이 없는 개인 프로그램이라 한 번 묻는 것입니다.

## 소스 실행

Windows에 Python이 있으면 저장소를 받은 뒤 프로젝트 폴더에서 실행합니다.

```powershell
python main.py
```

화면은 `tkinter`, 종료음은 `winsound`를 씁니다. 따로 설치할 패키지는 없습니다.

## 실행 파일 다시 만들기

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller.exe --noconfirm FocusTimer.spec
```

만들어진 파일은 `dist\FocusTimer.exe`입니다.
