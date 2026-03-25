@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()
        print(f"글로벌 슬래시 동기화 완료: {len(synced)}개")

    except Exception as e:
        print(e)

    print(f"{bot.user} 온라인")