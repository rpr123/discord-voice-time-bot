import discord
from discord.ext import commands,tasks
from datetime import datetime,time, timezone, timedelta
from dcclass import membermanager,FILE_NAME,os
import os

from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TOKEN')
guild_id = int(os.getenv('guild_id'))
channel = int(os.getenv('channel'))
channel_settelment = int(os.getenv('channel_settelment'))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

manager=membermanager()
__test=False

@bot.event
async def on_ready():
    guild = discord.Object(id=guild_id)

    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    #bot.tree.copy_global_to(guild=guild)
    #await bot.tree.sync(guild=guild)


    target_guild = bot.get_guild(guild_id)
    if target_guild:
        for voice_channel in target_guild.voice_channels:
            for member in voice_channel.members:
                # 봇 자신은 제외
                if not member.bot:
                    manager.enterexit(member.display_name, member.name, 'in')
                    print(f"봇 시작 시 감지: {member.display_name}({member.name}) - {voice_channel.name}에 접속 중")

    await bot.get_channel(channel).send("봇이 켜졌어요.")
    if __test:
        await bot.get_channel(channel).send(manager.printing_week())
    midnight_check.start()
    auto_save.start()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/print"))
    print(f'Login bot: {bot.user}')
    manager.load_in_progress_data()

KST = timezone(timedelta(hours=9))
midnight = time(hour=0, minute=0, second=00, tzinfo=KST)

@tasks.loop(time=midnight)
async def midnight_check():
    now = datetime.now()
    if now.weekday() == 0:
        await bot.get_channel(channel_settelment).send(manager.printing_week())    
    if now.day == 1:
        await bot.get_channel(channel_settelment).send(manager.printing_month())

@tasks.loop(minutes=5)
async def auto_save():
    manager.update() # 현재 접속 중인 인원 시간 갱신
    manager.save_in_progress_data()
    manager.save_stats() # 파일 저장
    print("데이터 자동 백업 완료")

@bot.event
async def on_voice_state_update(member, before, after):
    AB = bot.get_channel(channel)
    if after.channel is not None and before.channel is None:              #입장
        log_message = f'{member.display_name}({member.name}) 입갤'
        if AB:
            manager.enterexit(member.display_name,member.name,'in')
            await AB.send(log_message)
        else:
            print(f"Error: Could not find channel with ID {channel}")

    elif before.channel is not None and after.channel is None:                  #퇴장
        log_message = f'{member.display_name}({member.name}) 점점 멀어지네...'

        if AB:
            manager.enterexit(member.display_name,member.name,'out')
            await AB.send(log_message)
        else:
            print(f"Error: Could not find channel with ID {channel}")
    elif before.channel is not None and after.channel is not None and before.channel != after.channel:  #채널 이동
        log_message = f'{member.display_name}({member.name}) 채널 이동: {before.channel.name} → {after.channel.name}'
        if AB:
            # 이전 채널에서 퇴장 처리 (시간 정산)
            manager.enterexit(member.display_name,member.name,'out')
            # 새 채널에 입장 처리 (새로운 타임스탬프 시작)
            manager.enterexit(member.display_name,member.name,'in')
            await AB.send(log_message)
        else:
            print(f"Error: Could not find channel with ID {channel}")
    if before.self_mute != after.self_mute or before.mute != after.mute: # 음소거 상태 변경
        if after.mute or after.self_mute:
            await AB.send(f"{member.display_name}({member.name}) 음소거")
        else:
            await AB.send(f"{member.display_name}({member.name}) 음소거 해제")

@bot.tree.command(name="reset", description="현상태를 출력 후 초기화합니다")
async def reset(interaction: discord.Interaction):
    manager.update()
    await interaction.response.send_message(manager.printing())
    manager.reset()
    await interaction.followup.send("초기화")

@bot.tree.command(name="print", description="현상태를 출력합니다")
async def prt(interaction: discord.Interaction):
    manager.update()
    await interaction.response.send_message(manager.printing())

@bot.tree.command(name="get_json", description="현재 stats.json 파일을 업로드합니다")
async def get_json(interaction: discord.Interaction):
    # 최신 상태를 저장한 뒤 전송
    manager.update()
    manager.save_stats()
    
    if os.path.exists(FILE_NAME):
        await interaction.response.send_message("현재까지의 통계 파일입니다.", file=discord.File(FILE_NAME))
    else:
        await interaction.response.send_message("파일이 아직 생성되지 않았습니다.")

bot.run(TOKEN)
