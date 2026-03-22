import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# ==============================
# 設定ファイルの読み書き
# ==============================
SETTINGS_FILE = "settings.json"
RANKING_FILE = "ranking.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_ranking():
    if os.path.exists(RANKING_FILE):
        with open(RANKING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_ranking(data):
    with open(RANKING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==============================
# BOT初期設定
# ==============================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ==============================
# 起動時
# ==============================
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ {bot.user} が起動しました！")

# ==============================
# メッセージカウント（ランキング用）
# ==============================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    ranking = load_ranking()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if guild_id not in ranking:
        ranking[guild_id] = {}
    if user_id not in ranking[guild_id]:
        ranking[guild_id][user_id] = 0

    ranking[guild_id][user_id] += 1
    save_ranking(ranking)

    await bot.process_commands(message)

# ==============================
# /channel - チャンネル作成先カテゴリを設定
# ==============================
@tree.command(name="channel", description="チャンネル作成先のカテゴリIDを設定します")
@app_commands.describe(id="カテゴリID")
async def set_channel(interaction: discord.Interaction, id: str):
    settings = load_settings()
    guild_id = str(interaction.guild_id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]["create_category"] = id
    save_settings(settings)
    await interaction.response.send_message(f"✅ チャンネル作成先カテゴリを `{id}` に設定しました！", ephemeral=True)

# ==============================
# /dischannel - アーカイブカテゴリを設定
# ==============================
@tree.command(name="dischannel", description="アーカイブ先のカテゴリIDを設定します")
@app_commands.describe(id="アーカイブカテゴリID")
async def set_dischannel(interaction: discord.Interaction, id: str):
    settings = load_settings()
    guild_id = str(interaction.guild_id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]["archive_category"] = id
    save_settings(settings)
    await interaction.response.send_message(f"✅ アーカイブカテゴリを `{id}` に設定しました！", ephemeral=True)

# ==============================
# /create - チャンネル作成
# ==============================
@tree.command(name="create", description="新しいテキストチャンネルを作成します")
@app_commands.describe(name="チャンネル名")
async def create_channel(interaction: discord.Interaction, name: str):
    settings = load_settings()
    guild_id = str(interaction.guild_id)
    category = None

    if guild_id in settings and "create_category" in settings[guild_id]:
        category_id = int(settings[guild_id]["create_category"])
        category = interaction.guild.get_channel(category_id)

    new_channel = await interaction.guild.create_text_channel(name=name, category=category)
    await interaction.response.send_message(f"✅ チャンネル {new_channel.mention} を作成しました！", ephemeral=False)

# ==============================
# /remove - チャンネルをアーカイブへ移動
# ==============================
@tree.command(name="remove", description="このチャンネルをアーカイブカテゴリに移動します")
async def remove_channel(interaction: discord.Interaction):
    settings = load_settings()
    guild_id = str(interaction.guild_id)

    if guild_id not in settings or "archive_category" not in settings[guild_id]:
        await interaction.response.send_message("❌ アーカイブカテゴリが設定されていません。`/dischannel` で設定してください。", ephemeral=True)
        return

    category_id = int(settings[guild_id]["archive_category"])
    archive_category = interaction.guild.get_channel(category_id)

    if archive_category is None:
        await interaction.response.send_message("❌ アーカイブカテゴリが見つかりません。IDを確認してください。", ephemeral=True)
        return

    await interaction.channel.edit(category=archive_category)
    await interaction.response.send_message(f"📦 このチャンネルをアーカイブカテゴリ **{archive_category.name}** に移動しました。", ephemeral=False)

# ==============================
# /ranking - 発言数ランキング
# ==============================
@tree.command(name="ranking", description="サーバー内の発言数ランキングを表示します")
async def ranking(interaction: discord.Interaction):
    ranking_data = load_ranking()
    guild_id = str(interaction.guild_id)

    if guild_id not in ranking_data or not ranking_data[guild_id]:
        await interaction.response.send_message("📊 まだ発言データがありません！", ephemeral=False)
        return

    sorted_ranking = sorted(ranking_data[guild_id].items(), key=lambda x: x[1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, (user_id, count) in enumerate(sorted_ranking[:10]):
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"退出済みユーザー({user_id})"
        medal = medals[i] if i < 3 else f"**{i+1}位**"
        description += f"{medal} {name}　{count}回\n"

    embed = discord.Embed(
        title="📊 発言数ランキング",
        description=description,
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

# ==============================
# /setvc - VC予約チャンネルを設定
# ==============================
@tree.command(name="setvc", description="このチャンネルをVC予約通知チャンネルに設定します")
async def setvc(interaction: discord.Interaction):
    settings = load_settings()
    guild_id = str(interaction.guild_id)
    if guild_id not in settings:
        settings[guild_id] = {}
    settings[guild_id]["vc_channel"] = str(interaction.channel_id)
    save_settings(settings)
    await interaction.response.send_message(f"✅ {interaction.channel.mention} をVC予約チャンネルに設定しました！", ephemeral=True)

# ==============================
# /vcpln - VC予約
# ==============================
@tree.command(name="vcpln", description="指定時間後にVC開始予告を送ります（例: 10m, 1h）")
@app_commands.describe(time="時間（例: 10m, 1h, 30m）")
async def vcpln(interaction: discord.Interaction, time: str):
    settings = load_settings()
    guild_id = str(interaction.guild_id)

    if guild_id not in settings or "vc_channel" not in settings[guild_id]:
        await interaction.response.send_message("❌ VC予約チャンネルが設定されていません。`/setvc` で設定してください。", ephemeral=True)
        return

    # 時間パース
    seconds = 0
    if time.endswith("h"):
        try:
            seconds = int(time[:-1]) * 3600
        except ValueError:
            await interaction.response.send_message("❌ 時間の形式が正しくありません。例: `10m` や `1h`", ephemeral=True)
            return
    elif time.endswith("m"):
        try:
            seconds = int(time[:-1]) * 60
        except ValueError:
            await interaction.response.send_message("❌ 時間の形式が正しくありません。例: `10m` や `1h`", ephemeral=True)
            return
    else:
        await interaction.response.send_message("❌ 時間の形式が正しくありません。例: `10m` や `1h`", ephemeral=True)
        return

    user_name = interaction.user.display_name
    vc_channel_id = int(settings[guild_id]["vc_channel"])

    await interaction.response.send_message(f"⏰ {time}後にVC予告を送ります！", ephemeral=True)

    await asyncio.sleep(seconds)

    vc_channel = bot.get_channel(vc_channel_id)
    if vc_channel:
        await vc_channel.send(f"🎙️ **{user_name}** がVCを始めたがっています！")

# ==============================
# BOT起動
# ==============================
bot.run(os.getenv("DISCORD_TOKEN"))
