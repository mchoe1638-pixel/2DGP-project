BLADDER RUN 새 스프라이트 (방해꾼 12종 앞모습 + 1인칭 손 6종)

1. resource/image/npc, resource/image/arms 폴더를 게임의 resource/image/ 아래에 그대로 복사
2. manifest_추가항목.json 의 항목들을 resource/image/manifest.json 에 합치기
   (경로가 기존 manifest 형식과 다르면 file 값만 맞춰 주세요)
3. tools/ 의 gen_npc.py, gen_arms.py 로 다시 생성 가능 (pip install pillow, 실행하면 out/ 에 저장)
   - 색, 포즈를 바꾸고 싶으면 스크립트의 색상 코드나 좌표를 고친 뒤 다시 실행

npc_*_front : 288x144, 2프레임(144x144), f0 평소 / f1 반응, 발바닥은 하단 3px 위
arms_*      : 프레임 480x300, idle 2f / walk 4f / run 4f / jump 2f / hold 4f / fall 2f
npc_boss_front 대신 npc_bujang_front 를 쓰거나, 같은 파일을 npc_boss_front 키로 등록해도 됩니다.
