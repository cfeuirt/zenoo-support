import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

ROLES_STAFF = ['Fondateur', 'Modérateur', 'Staff']

def is_staff(member):
    return any(role.name in ROLES_STAFF for role in member.roles)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📩 Créer un ticket', style=discord.ButtonStyle.primary, custom_id='create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        existing = discord.utils.get(guild.text_channels, name=f'ticket-{member.name.lower()}')
        if existing:
            await interaction.response.send_message(f'Tu as déjà un ticket ouvert : {existing.mention}', ephemeral=True)
            return

        staff_roles = [discord.utils.get(guild.roles, name=r) for r in ROLES_STAFF]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for role in staff_roles:
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f'ticket-{member.name.lower()}',
            overwrites=overwrites
        )

        await interaction.response.send_message(f'Ton ticket a été créé : {channel.mention}', ephemeral=True)
        await channel.send(
            f'Bonjour {member.mention} ! Le staff va te répondre rapidement.\n\nStaff : utilisez les boutons ci-dessous.',
            view=StaffTicketView()
        )

class StaffTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='✅ Accepter', style=discord.ButtonStyle.success, custom_id='accept_ticket')
    async def accept_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return
        await interaction.response.send_message(f'✅ Ticket accepté par {interaction.user.mention} !')

    @discord.ui.button(label='🔒 Fermer', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return
        await interaction.response.send_message('🔒 Ticket fermé. Salon supprimé dans 5 secondes...')
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    await ctx.send('📩 Clique sur le bouton pour créer un ticket :', view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(StaffTicketView())
    print(f'Bot connecté : {bot.user}')

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
