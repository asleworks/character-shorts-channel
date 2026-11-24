# 그림 없는 카드 예시

배포 저장소에는 음성 파일을 넣지 않았어요. 직접 녹음하거나, macOS라면 아래처럼 시스템 음성으로 테스트용 파일을 만들어 쓰세요.

```bash
say -v Yuna -r 175 -o /tmp/card.aiff "알람을 자꾸 미루나요? 오늘은 딱 한 가지만 바꿔 봐요. 알람은 하나만 남기고, 휴대폰은 침대에서 떨어진 곳에 둬요. 벨이 울리면 먼저 두 발을 바닥에 내려놓으세요."
ffmpeg -i /tmp/card.aiff examples/card_only/narration.mp3
```

`words.json`은 위 문장 기준 타이밍이에요. 다른 녹음을 쓰면 `--words`를 빼고 실행해 자동으로 타이밍을 만드세요.
