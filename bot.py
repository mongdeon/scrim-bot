import discord
from discord.ext import commands
import asyncio
from core.config import TOKEN

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"글로벌 슬래시 동기화 완료: {len(synced)}개")
    except Exception as e:
        print(f"슬래시 동기화 오류: {e}")

    print(f"{bot.user} 온라인")


@bot.event
async def on_voice_state_update(member, before, after):
    # 누군가 음성채널에서 나갔을 때만 체크
    if before.channel and isinstance(before.channel, discord.VoiceChannel):
        channel = before.channel

        # 대기방만 대상으로 함
        if channel.name.endswith("대기방"):
            # 상태 반영 시간 조금 기다림
            await asyncio.sleep(1)

            # 채널 다시 가져오기
            refreshed_channel = member.guild.get_channel(channel.id)

            # 채널이 아직 있고, 비어 있으면 삭제
            if refreshed_channel and isinstance(refreshed_channel, discord.VoiceChannel):
                if len(refreshed_channel.members) == 0:
                    try:
                        await refreshed_channel.delete(reason="대기방 인원 0명 자동 삭제")
                        print(f"대기방 자동 삭제: {refreshed_channel.name}")
                    except Exception as e:
                        print(f"대기방 삭제 실패: {e}")


# ⭐ 봇 상태 확인 명령어
@bot.tree.command(name="핑", description="봇 상태 확인")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("퐁 🏓")


async def main():
    async with bot:
        await bot.load_extension("cogs.settings_cog")
        await bot.load_extension("cogs.recruit_cog")
        await bot.load_extension("cogs.team_cog")
        await bot.load_extension("cogs.ranking_cog")
        await bot.load_extension("cogs.profile_cog")
        await bot.load_extension("cogs.help_cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())