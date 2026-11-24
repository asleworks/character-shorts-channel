# Higgsfield 그림 프롬프트

각 후보와 장면은 정사각형 한 장으로 요청한다. 참조 이미지는 프롬프트에 적은 순서대로 전달한다. 그림에 들어갈 글자와 수치는 `scenes.json`의 `screen_text`에 따로 기록한다.

그림을 생성하거나 편집하기 전에 작업 환경의 이미지 프롬프팅 규칙을 읽는다. 결과는 글자·수치, 캐릭터 외형, 바뀐 부분, 비율·크기를 대조하고 투명을 요청했다면 알파 채널도 확인해 보고한다.

## 캐릭터 후보

후보마다 종, 실루엣, 한눈에 보이는 특징을 바꿔 각각 요청한다. 사용자가 고른 그림을 이후의 Image 1로 쓴다.

```text
Asset type: A single full-body mascot design for a vertical short.
Use: Square character reference, to be reused in later shots.
Subject: <species or object>, <permanent traits>, <pose that expresses the selected personality>.
Style/medium: <chosen drawing medium, visible line and fill treatment>.
Composition: One large centered figure in a simple front-facing pose, all limbs visible.
Lighting & color: <one main color>, flat light, plain pure white background.
Materials: Opaque flat color with simple marker outlines.
Text (verbatim): None.
Input images: None.
Constraints: Keep the silhouette simple and readable at thumbnail size.
Avoid: Text, letters, numbers, logos, watermarks and backgrounds other than white.
```

## 표정 기준 시트

```text
Asset type: One square expression sheet for <NAME>.
Use: Image 2 for later scenes.
Subject: Same character as Image 1 (<NAME>: <short appearance description>).
Style/medium: Preserve the line treatment and fill from Image 1.
Composition: A 3-by-2 grid of the same character. Top row: blank, delighted, confused.
Bottom row: worried, annoyed, angry. Each panel has the same framing and scale.
Lighting & color: Flat fills on plain pure white.
Materials: Preserve the simple marker outlines.
Text (verbatim): None.
Input images: Image 1 = chosen base character.
Constraints: Do not redesign the character. Keep the silhouette, palette, limb lengths
and permanent features fixed. <Where a strong emotion changes one visible detail, specify it.>
Avoid: Labels, text, letters, numbers, logos, watermarks and unrequested cheek blush.
```

## 강한 감정 기준 그림

```text
Asset type: One square full-body reference for <NAME> showing <EMOTION>.
Use: Image 3 in scenes featuring that emotion.
Subject: Same <NAME> as Image 1 (<permanent silhouette, palette and features>).
Style/medium: Preserve the line treatment and fill from Image 1.
Composition: One large centered figure, all limbs visible, <emotion-specific pose>.
Lighting & color: Plain white background, <unchanged palette>, <one emotion cue>.
Materials: Preserve the original surface and outline treatment.
Text (verbatim): None.
Input images: Image 1 = chosen base character. Image 2 = expression sheet.
Constraints: Do not redesign the character. Change only the expression, pose
and the specified emotion cue: <what changes, where, and what stays the same>.
Avoid: Extra color changes, labels, letters, numbers, logos and watermarks.
```

가사리의 화난 버전은 머리 끝만 빨개지고 볼은 노란색을 유지한다.

## 장면 그림

프로필의 `character.prompt_prefix`를 Subject에 이어 붙인다. 강한 감정 기준을 쓸 때만 Image 3을 추가한다.

```text
Asset type: One square illustration for short scene <SCENE_KEY>.
Use: Character art for a vertical short with title and captions added separately.
Subject: <profile prompt prefix>, <pose, expression and props for this scene>.
Style/medium: <the channel's drawing style>.
Composition: <framing and prop placement>, one large character, blank label areas.
Lighting & color: <channel palette>, plain pure white background.
Materials: <channel texture or outline treatment>.
Text (verbatim): None.
Input images: Image 1 = base character. Image 2 = expression guide.
Constraints: Do not redesign the character. Preserve the permanent features.
Avoid: Text, letters, numbers, logos and watermarks.
```

강한 감정 기준을 쓸 때는 Input images의 Image 2 다음에 `Image 3 = <emotion> look.`을 더하고 그 그림을 세 번째로 전달한다.

### Higgsfield 이미지 배치

`generate_image_batch`에 넘기는 장면 요청 예시다. 후보 생성에는 `medias`를 생략하고 표정 시트에는 기본 그림만 넣는다. 감정 기준 그림에는 기본 그림과 표정 시트를 넣는다.

```json
{
  "requests": [
    {
      "index": 0,
      "params": {
        "model": "gpt_image_2_6",
        "prompt": "<SCENE_PROMPT>",
        "aspect_ratio": "1:1",
        "medias": [
          {"value": "<JOB_ID>", "role": "image_references"},
          {"value": "<JOB_ID>", "role": "image_references"}
        ]
      }
    }
  ]
}
```

장면 번호와 배치의 `index`를 대응시킨다. `jobs_wait`에 `{"jobs":[{"index":0,"job_id":"<JOB_ID>"}],"timeout_seconds":15}`를 전달하고, 진행 중인 항목은 도구가 반환한 대기 간격에 맞춰 같은 ID로 조회한다. 배치 한도는 연결된 도구 설명을 따른다.

## 음성 샘플과 본편

`generate_audio_batch`에서 샘플은 말투와 목소리 조합마다 요청 항목 하나, 본편은 전체 대사를 한 항목에 넣는다. 본편의 `voice_id`, 모델, `stability`에는 프로필 값을 사용한다.

```json
{
  "requests": [
    {
      "index": 0,
      "params": {
        "model": "elevenlabs_v4",
        "prompt": "<VOICE_DIRECTION>",
        "dialogue": [{"text": "<READ_ALOUD_TEXT>", "voice_id": "<VOICE_ID>", "voice_type": "preset"}],
        "stability": 0.5
      }
    }
  ]
}
```

## 실제 예시 · 가사리 S01

```text
Same character as Image 1: Gasari, a hand-drawn mustard-yellow starfish mascot with a thick wobbly black marker outline, flat fill, one arm noticeably shorter, the top tip leaning slightly. Image 2 is the expression guide. Do not redesign the character. Clumsy hand-drawn MS-Paint doodle style, flat colors, simple props, plain pure white background, square frame, character large and centered. No text, no letters, no numbers, no logos anywhere. Scene: Gasari lying in bed under a blanket pulled up to the chin, dazed blank stare.
```

[예시 결과](../examples/gasari/images/S01.webp)
