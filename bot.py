import os
from datetime import datetime, time, timezone, timedelta

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from voice_tracker import FILE_NAME, MemberManager


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID") or os.getenv("guild_id"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID") or os.getenv("channel"))
SETTLEMENT_CHANNEL_ID = int(
    os.getenv("SETTLEMENT_CHANNEL_ID") or os.getenv("channel_settelment")
)

KST = timezone(timedelta(hours=9))
MIDNIGHT = time(hour=0, minute=0, second=0, tzinfo=KST)
TEST_MODE = False

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
manager = MemberManager()


def get_log_channel():
    return bot.get_channel(LOG_CHANNEL_ID)


def get_settlement_channel():
    return bot.get_channel(SETTLEMENT_CHANNEL_ID)


async def send_log(message):
    channel = get_log_channel()
    if channel:
        await channel.send(message)
    else:
        print(f"Error: Could not find channel with ID {LOG_CHANNEL_ID}")


@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    target_guild = bot.get_guild(GUILD_ID)
    if target_guild:
        for voice_channel in target_guild.voice_channels:
            for member in voice_channel.members:
                # 봇 자신은 제외
                if not member.bot:
                    manager.enter_exit(member.display_name, member.name, "in")
                    print(
                        f"봇 시작 시 감지: {member.display_name}({member.name}) "
                        f"- {voice_channel.name}에 접속 중"
                    )

    await send_log("봇이 켜졌어요.")
    if TEST_MODE:
        await send_log(manager.print_week())

    midnight_check.start()
    auto_save.start()
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="/print")
    )
    print(f"Login bot: {bot.user}")
    manager.load_in_progress_data()


@tasks.loop(time=MIDNIGHT)
async def midnight_check():
    now = datetime.now()
    settlement_channel = get_settlement_channel()
    if not settlement_channel:
        print(f"Error: Could not find channel with ID {SETTLEMENT_CHANNEL_ID}")
        return

    if now.weekday() == 0:
        await settlement_channel.send(manager.print_week())
    if now.day == 1:
        await settlement_channel.send(manager.print_month())


@tasks.loop(minutes=5)
async def auto_save():
    manager.update()  # 현재 접속 중인 인원 시간 갱신
    manager.save_in_progress_data()
    manager.save_stats()
    print("데이터 자동 백업 완료")


@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel is not None and before.channel is None:
        manager.enter_exit(member.display_name, member.name, "in")
        await send_log(f"{member.display_name}({member.name}) 입갤")

    elif before.channel is not None and after.channel is None:
        manager.enter_exit(member.display_name, member.name, "out")
        await send_log(f"{member.display_name}({member.name}) 점점 멀어지네...")

    elif (
        before.channel is not None
        and after.channel is not None
        and before.channel != after.channel
    ):
        manager.enter_exit(member.display_name, member.name, "out")
        manager.enter_exit(member.display_name, member.name, "in")
        await send_log(
            f"{member.display_name}({member.name}) 채널 이동: "
            f"{before.channel.name} → {after.channel.name}"
        )

    if before.self_mute != after.self_mute or before.mute != after.mute:
        status = "음소거" if after.mute or after.self_mute else "음소거 해제"
        await send_log(f"{member.display_name}({member.name}) {status}")


@bot.tree.command(name="reset", description="현상태를 출력 후 초기화합니다")
async def reset(interaction: discord.Interaction):
    manager.update()
    await interaction.response.send_message(manager.print_current())
    manager.reset()
    await interaction.followup.send("초기화")


@bot.tree.command(name="print", description="현상태를 출력합니다")
async def prt(interaction: discord.Interaction):
    manager.update()
    await interaction.response.send_message(manager.print_current())


@bot.tree.command(name="get_json", description="현재 stats.json 파일을 업로드합니다")
async def get_json(interaction: discord.Interaction):
    # 최신 상태를 저장한 뒤 전송
    manager.update()
    manager.save_stats()

    if os.path.exists(FILE_NAME):
        await interaction.response.send_message(
            "현재까지의 통계 파일입니다.", file=discord.File(FILE_NAME)
        )
    else:
        await interaction.response.send_message("파일이 아직 생성되지 않았습니다.")


bot.run(TOKEN)
