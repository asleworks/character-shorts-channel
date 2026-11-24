---
name: faceless-character-shorts
description: 가사리처럼 한 캐릭터가 등장하는 세로 쇼츠를 주제에서 대본, 장면 그림, 내레이션, 자막, MP4까지 만든다. Use when asked to make a faceless or mascot-led short with Higgsfield and Claude.
---

# 캐릭터 쇼츠 공장

이 작업에 연결된 Higgsfield MCP 도구를 확인한다. 프로젝트 산출물은 작업 폴더에 두고 스킬 폴더는 재사용한다. 크레딧이 드는 단계마다 실행하기 전에 모델, 생성 수량, 예상 비용을 사용자에게 말한다. 연결된 도구에서 견적을 받을 수 있으면 우선한다. 실측 참고치는 기본 GPT Image 2.6 장당 0.75크레딧, 고화질 장당 1.25크레딧, Eleven v4 샘플 1개 약 0.69크레딧, 70초 본편 약 2.76크레딧이다.

## 1. 주제에서 대본 작성

[대본 공식](references/formula.md)을 읽고 채워진 공식과 장면 양식을 적용한다. 사용자가 준 주제와 말투를 반영해 장면마다 대사와 그림 설명을 쓴다. 내레이션에 들어갈 대사와 화면에만 표시할 문구를 별도로 기록한다. 기존 대본이 있으면 그 원문과 순서를 기준으로 삼는다.

## 2. 캐릭터와 표정 확정

캐릭터가 없으면 [그림 프롬프트](references/prompts.md)로 서로 다른 후보를 여러 장 만들고, 번호를 붙여 보여 준다. 사용자가 후보를 고르면 그 그림을 기본 참조로 저장하고 표정 기준 시트 한 장을 생성한다. 기존 캐릭터나 표정 시트가 있으면 재사용한다. 강한 감정이 반복되면 그 감정만 크게 보여 주는 기준 그림을 준비한다.

## 3. 장면 그림 생성

한 편의 장면을 한꺼번에 계획하고, 도구의 배치 한도에 맞춰 묶어 제출한다. Image 1은 기본 그림, Image 2는 표정 시트, Image 3은 해당 장면에 필요한 강한 감정의 기준 그림이다. 각 장면 프롬프트에 외형과 표정, 소품, 배치를 명시하고 글자 자리를 비운다. 그림을 확인한 뒤 수정이 필요한 장면만 다시 생성한다. [자주 겪는 문제](references/pitfalls.md)

Higgsfield MCP 호출 예시

```json
{
  "requests": [
    {
      "index": 0,
      "params": {
        "model": "gpt_image_2_6",
        "prompt": "<scene_prompt>",
        "aspect_ratio": "1:1",
        "medias": [
          {"value": "<base_job_id>", "role": "image_references"},
          {"value": "<expression_sheet_job_id>", "role": "image_references"}
        ]
      }
    }
  ]
}
```

`generate_image_batch`에서 후보의 `medias`는 생략하고 표정 시트에는 기본 그림 하나만 넣는다. 장면과 배치의 `index`를 대응시켜 결과를 올바른 파일에 저장한다. 기다릴 때는 `jobs_wait`에 `{"jobs":[{"index":0,"job_id":"<returned_job_id>"}],"timeout_seconds":15}`를 넘긴다. 아직 진행 중이면 반환된 대기 간격에 맞춰 같은 ID를 조회한다. 연결된 도구의 실제 배치 한도와 결과 표시 방식은 도구 설명에 따른다.

## 4. 내레이션 생성

한국어면 숫자나 캐릭터 이름이 들어간 짧은 대사로 Eleven v4 목소리 후보를 시험한다. 후보 음성을 직접 들을 수 있게 제공하고, 사용자가 고르면 선택한 프리셋으로 전체 대사를 순서대로 읽힌다. 말투와 발음이 맞는지 최종 음원을 확인하고 MP3로 준비한다. 이미 녹음한 MP3를 받은 경우 그 파일을 쓴다.

`generate_audio_batch`의 요청 예시. 샘플은 프리셋마다 항목 하나, 본편은 전체 대사를 한 항목에 넣는다.

```json
{
  "requests": [
    {
      "index": 0,
      "params": {
        "model": "elevenlabs_v4",
        "prompt": "<voice_direction>",
        "dialogue": [{"text": "<read_aloud_text>", "voice_id": "<preset_voice_id>", "voice_type": "preset"}],
        "stability": 0.5
      }
    }
  ]
}
```

## 5. 자막과 컷 렌더

순서가 있는 `scenes.json`에 `key`, `dialogue`, `image`, `screen_text`를 적는다. `image`는 JSON 기준 경로이며 `screen_text`는 화면에만 표시할 문자열 배열이다. [입력 예시](examples/gasari/scenes.json)

단어 타이밍이 있으면 원본 음성 기준 초 단위의 `[{"w":"단어","s":0.05,"e":0.48}]`를 `--words`로 전달한다. 생략하면 faster-whisper가 생성한다. 장면의 첫 단어에 맞춰 컷을 전환하고 자막에는 대본 원문을 쓴다.

```bash
python3 scripts/render.py --scenes work/scenes.json --audio work/narration.mp3 \
  --language ko --out work/out
```

스킬 루트에서 실행하거나 스크립트의 전체 경로를 사용한다. 설치와 글꼴 옵션은 [README](README.md)를 참고한다. claude.ai 실행 환경에서 FFmpeg나 의존성을 사용할 수 없으면 그림, 음성, `scenes.json`과 타이밍 파일을 내려받아 로컬에서 렌더하도록 제공한다.

## 6. 검수 및 전달

`sheet_scenes.jpg`에서 장면 그림과 화면 문구를 대조한다. MP4를 재생해 컷이 해당 대사의 발화에 맞는지, 자막이 대본과 같은지, 이름과 숫자가 정확한지 확인한다. `REPORT.md`에서 최종 음량이 −14 LUFS 부근이고 최대 트루 피크가 −1 dBTP 이하인지 확인한다. 타이밍이 어긋나면 단어 시각을 수정해 다시 렌더한다. 완성한 1080×1920 MP4, 장면 시트, 보고서를 전달한다.
