# Higgsfield 그림 프롬프트

각 후보와 장면은 정사각형 한 장으로 요청한다. 참조 이미지는 프롬프트에 적은 순서대로 전달한다. 그림에 들어갈 글자와 수치는 `scenes.json`의 `screen_text`에 따로 기록한다.

## 캐릭터 후보

후보마다 종, 실루엣, 한눈에 보이는 특징을 바꿔 각각 요청한다. 사용자가 고른 그림을 이후의 Image 1로 쓴다.

```text
Asset type: A single full-body mascot design for a vertical short.
Use: Square character reference, to be reused in later shots.
Subject: <species or object>, <two permanent traits such as one short arm and a slanted top>.
Style/medium: Clumsy MS-Paint doodle, thick wobbly black marker outlines, flat fills.
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
Style/medium: Keep the MS-Paint doodle outlines and flat color from Image 1.
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

강한 감정의 단독 기준 그림이 필요하면 Image 1과 표정 시트를 넣고, 그 표정 하나를 크게 보여 주는 정사각형을 요청한다. 가사리의 화난 버전은 머리 끝만 빨개지고 볼은 노란색을 유지한다.

## 장면 공통 문장

```text
Same character as Image 1 (<NAME>: <short appearance description>). Image 2 = expression guide. Do not redesign the character. MS-Paint doodle style, plain pure white background, square, character large. No text, letters, numbers or logos. Scene: <pose, expression, prop and framing>.
```

강한 감정 기준을 쓸 때는 Image 2 설명 다음에 `Image 3 = <emotion> look.`을 더하고 그 그림을 세 번째로 전달한다. 소품에 글자가 들어갈 자리는 비워 달라고 지시한다. 볼 홍조가 생긴 컷에는 `No red cheek blush.`를 더해 다시 생성한다.

## 실제 예시 · 가사리 S01

```text
Same character as Image 1: Gasari, a hand-drawn mustard-yellow starfish mascot with a thick wobbly black marker outline, flat fill, one arm noticeably shorter, the top tip leaning slightly. Image 2 is the expression guide. Do not redesign the character. Clumsy hand-drawn MS-Paint doodle style, flat colors, simple props, plain pure white background, square frame, character large and centered. No text, no letters, no numbers, no logos anywhere. Scene: Gasari lying in bed under a blanket pulled up to the chin, dazed blank stare.
```

[예시 결과](../examples/gasari/images/S01.webp)
