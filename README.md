# 캐릭터 쇼츠 공장

가사리 같은 캐릭터로 세로 쇼츠 한 편을 만드는 Claude 스킬입니다. 주제를 주면 대본을 쓰고, Higgsfield MCP로 장면 그림과 내레이션을 만든 뒤, 대본 자막을 입힌 1080×1920 MP4로 조립합니다.

## 설치

**Claude Code**에서 이 저장소의 상위 폴더에서 실행하세요. 개인 스킬은 `~/.claude/skills/`에 둡니다. [Claude Code 스킬 문서](https://code.claude.com/docs/en/skills)

```bash
mkdir -p ~/.claude/skills/faceless-character-shorts
cp -R faceless-character-shorts/SKILL.md faceless-character-shorts/README.md \
  faceless-character-shorts/references faceless-character-shorts/scripts \
  faceless-character-shorts/examples ~/.claude/skills/faceless-character-shorts/
```

**claude.ai**에서는 설정의 **Capabilities**에서 코드 실행과 파일 생성을 켭니다. **Customize → Skills → + → Upload a skill**에서 `faceless-character-shorts` 폴더를 담은 ZIP을 업로드합니다. Git으로 받은 저장소라면 스킬 폴더에서 아래 명령으로 ZIP을 만듭니다. GitHub에서 소스 ZIP을 받았다면 먼저 압축을 풀고, 폴더 이름을 `faceless-character-shorts`로 바꾼 후 폴더째 압축합니다. [Claude 맞춤 스킬 도움말](https://support.claude.com/en/articles/12512180-use-skills-in-claude)

```bash
git archive --format=zip --prefix=faceless-character-shorts/ \
  --output=../faceless-character-shorts.zip HEAD
```

## Higgsfield 연결

- **Claude Code**에서 HTTP MCP 서버를 추가한 다음 Claude Code의 `/mcp`에서 Higgsfield 계정으로 인증합니다. [Claude Code MCP 문서](https://code.claude.com/docs/en/mcp)
- **claude.ai**에서 **Customize → Connectors**로 이동해 사용자 지정 커넥터를 추가합니다. 이름에 `Higgsfield`, URL에 `https://mcp.higgsfield.ai/mcp`를 입력하고 Higgsfield 계정으로 로그인합니다. 대화에서 커넥터를 사용할 수 있는지 확인합니다. [Higgsfield MCP 안내](https://higgsfield.ai/mcp)

```bash
claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp
```

## 사용 예시

> 가사리 같은 캐릭터로 ‘알람을 자꾸 미루는 이유’ 쇼츠 만들어 줘. 해요체로 읽고, 캐릭터 후보와 한국어 목소리 샘플을 내가 고르게 해 줘.

[가사리 예시](examples/gasari/script.md)에는 1편 전체 대본이 있습니다. [렌더 입력 예시](examples/gasari/scenes.json)는 첫 네 컷과 약 15초 분량의 대사만 담았습니다. 네 번째 대사는 발췌 중간에서 끝납니다. 그림 네 장은 WebP로 들어 있고 내레이션 MP3는 별도로 준비해야 합니다.

## 예상 비용

70초 안팎 한 편의 Higgsfield 사용 예시입니다. 원화는 2026년 11월 제작 당시 Ultra 연간 약 20.4원, 월간 약 34원으로 계산했습니다. 현재 비용은 계정의 견적과 생성 설정에 따라 달라집니다.

| 방식 | Higgsfield 크레딧 | 연간 환산 | 월간 환산 |
|---|---:|---:|---:|
| 직접 녹음하고 가지고 있는 그림으로 조립 | 0 | 0원 | 0원 |
| Eleven v4 내레이션만 생성 | 약 2.76 | 약 56원 | 약 94원 |
| Eleven v4 내레이션과 기본 화질 그림 16장 생성 | 약 14.76 | 약 301원 | 약 502원 |

캐릭터 후보, 표정 시트, 목소리 샘플, 재생성에는 별도 크레딧이 듭니다. 기본 GPT Image 2.6 장당 0.75크레딧과 약 70초 내레이션 실측치를 적용했습니다.

## 로컬 렌더

macOS 또는 Linux에서 Python 3.10 이상(예시 검증은 3.12)과 `ffmpeg` 및 `ffprobe`가 필요합니다. FFmpeg는 H.264용 `libx264`와 AAC 인코더가 있는 빌드를 쓰세요. 스킬 폴더에서 실행합니다.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
python3 scripts/render.py --scenes work/scenes.json --audio work/narration.mp3 \
  --language ko --out work/out
```

- `scenes.json`은 재생 순서대로 정렬한 배열입니다. 각 항목에 고유한 `key`, 녹음과 같은 `dialogue`, JSON 파일에서 상대 경로로 읽는 `image`, 선택 항목인 `screen_text` 문자열 배열을 적습니다.
- 기존 단어 타이밍은 `--words work/words.json`으로 전달합니다. 형식은 `[{"w":"알람을","s":0.05,"e":0.46}]`이며 `s`와 `e`는 원본 음성 기준 초입니다.
- `--words`를 생략하면 faster-whisper가 단어 시각을 추정합니다. 처음 사용할 때 모델을 내려받습니다. `--whisper-model`로 모델 이름이나 내려받은 모델 폴더를 지정할 수 있습니다.
- 시스템에서 한글 글꼴을 찾지 못하면 `--font /path/to/NotoSansKR.ttf`를 추가합니다.
- 출력은 `short.mp4`, `sheet_scenes.jpg`, `REPORT.md`입니다. 보고서에서 음량과 자막 대조 결과를 확인한 뒤, 영상을 재생해 실제 발화와 컷을 비교하세요.

claude.ai의 코드 실행 환경에서 렌더 의존성을 사용할 수 없으면 생성한 그림, MP3, 장면 JSON을 내려받아 위 명령으로 로컬에서 조립할 수 있습니다.

## English summary

A Claude skill for creating a vertical short around a recurring mascot. It drafts a scene script, uses Higgsfield MCP for consistent illustrations and Eleven v4 narration, then renders an H.264 MP4 with script-based captions, a scene sheet, and a QA report.

Copy the skill to `~/.claude/skills/faceless-character-shorts/` for Claude Code or upload a ZIP of the skill through **Customize → Skills** on claude.ai. Connect Higgsfield at `https://mcp.higgsfield.ai/mcp`. The local renderer requires Python and FFmpeg on macOS or Linux. Using your own art and narration costs 0 Higgsfield credits. The recorded example cost about 2.76 credits for the narration and 14.76 credits with 16 images.
