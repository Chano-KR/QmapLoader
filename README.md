# QmapLoader 사용 안내

QmapLoader는 PDF를 Markdown으로 바꿔주는 로컬 Windows 앱입니다. 프로그램을 설치한 뒤 바탕화면 아이콘을 더블클릭하면 브라우저에서 바로 사용할 수 있습니다.

## 준비 사항

- Windows
- Java 11 이상

Python이 없으면 설치 스크립트가 `winget`으로 자동 설치를 제안합니다. `Y/N` 확인 후 진행하는 방식입니다.

## 설치 방법

GitHub 저장소 링크만 있으면 PowerShell에서 바로 설치할 수 있습니다.

1. 아래 명령어를 복사합니다.
2. PowerShell을 엽니다.
3. 아래 명령어를 붙여넣습니다.

```powershell
$repo = 'https://github.com/Chano-KR/QmapLoader'
$branch = 'main'
$temp = Join-Path $env:TEMP 'qmaploader-bootstrap.ps1'
Invoke-WebRequest "$repo/raw/$branch/installer/bootstrap.ps1" -OutFile $temp
powershell -ExecutionPolicy Bypass -File $temp -RepoUrl $repo -Branch $branch
```

4. 설치가 끝나면 바탕화면에 `QmapLoader` 아이콘이 생성됩니다.

기존 방식처럼 저장소를 직접 내려받은 뒤 `installer\install.ps1`를 실행해도 됩니다.

설치 스크립트가 하는 일:

- GitHub 저장소 zip 다운로드 및 설치 폴더 복사
- Python 버전 확인, 필요 시 `winget` 자동 설치 제안
- Java 설치 여부 확인
- `.venv` 가상환경 생성 또는 재사용
- 필요한 Python 패키지 설치
- 바탕화면 바로가기 생성

## 실행 방법

1. 바탕화면의 `QmapLoader` 아이콘을 더블클릭합니다.
2. 잠시 후 브라우저가 자동으로 열립니다.
3. PDF 파일을 끌어다 놓거나 선택해서 업로드합니다.
4. 변환이 끝나면 Markdown 파일을 다운로드합니다.
5. 필요하면 결과 폴더 열기 버튼으로 저장 위치를 바로 열 수 있습니다.

## 결과 저장 위치

기본 저장 위치:

```text
내 문서\QmapLoader\outputs
```

환경 설정을 바꾸지 않았다면 결과 파일은 여기에 저장됩니다.

## 알아두면 좋은 점

- 기본 포트는 `5786`입니다.
- `5786`이 이미 사용 중이면 자동으로 `8765`를 사용합니다.
- 창에 실행 주소가 `http://127.0.0.1:8765/`처럼 보일 수 있는데, 이것은 정상입니다.

## 문제 해결

- 실행이 안 되면 `installer\install.ps1`를 다시 실행해 보세요.
- GitHub 설치 명령을 썼다면 같은 명령을 다시 실행해서 파일을 덮어쓴 뒤 복구할 수 있습니다.
- Python이 없다는 안내가 나오면 설치 스크립트의 `Y` 선택으로 자동 설치를 진행할 수 있습니다.
- 변환이 바로 실패하면 화면에 표시되는 안내 문구를 먼저 확인하세요.
- `Java를 찾을 수 없습니다` 또는 Java 버전 관련 문구가 나오면 Java 11 이상이 설치되어 있는지 확인하세요.
- 결과 폴더 저장 오류가 나오면 출력 폴더 권한과 디스크 공간을 확인하세요.
- 바탕화면 아이콘 대신 `launcher\run_qmaploader.bat`를 직접 실행해도 됩니다.

## 현재 상태

- PDF 변환 기능 동작함
- 웹 UI 동작함
- 설치 스크립트와 바탕화면 실행 동작함
- 남은 작업은 문서 보강, 에러 메시지 개선, 로그 정리 위주입니다
