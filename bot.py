import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

GUILD_ID = 1506035311048917052
CATEGORY_NAME = "Besoin d'aide 🆘"
STAFF_ROLES = ['Fondateur', 'Modérateur', 'Staff']
MOD_FILE = 'mods.json'

def load_mods():
    if os.path.exists(MOD_FILE):
        with open(MOD_FILE, 'r') as f:
            return json.load(f)
    return {}

class TicketButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Créer un ticket', style=discord.ButtonStyle.green, custom_id='create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        existing = discord.utils.get(guild.channels, name=f'ticket-{interaction.user.name.lower()}')
        if existing:
            await interaction.response.send_message('❌ Tu as déjà un ticket ouvert!', ephemeral=True)
            return
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_name in STAFF_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await guild.create_text_channel(
            f'ticket-{interaction.user.name.lower()}',
            category=category,
            overwrites=overwrites
        )
        close_view = CloseView()
        claim_view = ClaimView()
        combined = CombinedView()
        await channel.send(
            f'👋 Bonjour {interaction.user.mention} ! Un membre du staff va vous répondre.\n\nUtilisez les boutons ci-dessous :',
            view=combined
        )
        await interaction.response.send_message(f'✅ Ticket créé : {channel.mention}', ephemeral=True)

class CombinedView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ Claim', style=discord.ButtonStyle.blurple, custom_id='claim_ticket')
    async def claim_ticket(self, interaction: discord.Interaction, button: Button):
        mods = load_mods()
        numero = mods.get(str(interaction.user.id))
        if numero:
            await interaction.response.send_message(f'Le modérateur {numero} a pris votre ticket.')
        else:
            await interaction.response.send_message(f'{interaction.user.display_name} a pris votre ticket.')

    @discord.ui.button(label='🔒 Fermer', style=discord.ButtonStyle.red, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message('🔒 Fermeture du ticket...')
        await interaction.channel.delete()

@bot.event
async def on_ready():
    bot.add_view(TicketButton())
    bot.add_view(CombinedView())
    print(f'Bot tickets connecte : {bot.user}')

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    embed = discord.Embed(
        title='🎫 Support Zenoo RP',
        description='Clique sur le bouton ci-dessous pour ouvrir un ticket.\nNotre staff vous répondra dès que possible.',
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=TicketButton())
    await ctx.message.delete()

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
