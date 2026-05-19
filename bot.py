import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

ROLES_STAFF = ['Fondateur', 'Modérateur', 'Staff']
tickets = {}

def is_staff(member):
    return any(role.name in ROLES_STAFF for role in member.roles)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🎫 Ouvrir un ticket', style=discord.ButtonStyle.primary, custom_id='open_ticket')
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild = interaction.guild

        if member.id in tickets:
            await interaction.response.send_message('❌ Tu as déjà un ticket ouvert !', ephemeral=True)
            return

        try:
            await member.send('📩 Ton ticket a été ouvert ! Merci de patienter, un membre du staff va accepter ou refuser ta demande.')
        except:
            await interaction.response.send_message('❌ Je ne peux pas t\'envoyer de MP ! Active tes MPs.', ephemeral=True)
            return

        staff_roles = [discord.utils.get(guild.roles, name=r) for r in ROLES_STAFF]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }
        for role in staff_roles:
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f'ticket-{member.name.lower()}',
            overwrites=overwrites
        )

        tickets[member.id] = {'channel': channel.id, 'status': 'pending'}

        await channel.send(
            f'📩 Nouveau ticket de **{member.name}**\nUtilisez les boutons pour accepter ou refuser.',
            view=StaffView(member.id)
        )

        await interaction.response.send_message('✅ Ticket ouvert ! Vérifie tes MPs.', ephemeral=True)

class StaffView(discord.ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @discord.ui.button(label='✅ Accepter', style=discord.ButtonStyle.success, custom_id='accept_ticket')
    async def accept_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return

        member = interaction.guild.get_member(self.member_id)
        if member:
            await member.send(f'✅ Ton ticket a été **accepté** par **{interaction.user.name}** ! Tu peux maintenant expliquer ton problème ici en MP.')
            tickets[self.member_id]['status'] = 'accepted'
            tickets[self.member_id]['staff_channel'] = interaction.channel.id

        await interaction.response.send_message(f'✅ Ticket accepté par {interaction.user.mention} ! Écrivez dans ce salon pour parler au membre.')
        await interaction.message.edit(view=CloseView(self.member_id))

    @discord.ui.button(label='❌ Refuser', style=discord.ButtonStyle.danger, custom_id='refuse_ticket')
    async def refuse_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return

        member = interaction.guild.get_member(self.member_id)
        if member:
            await member.send(f'❌ Ton ticket a été **refusé** par **{interaction.user.name}**.')

        channel_id = tickets[self.member_id]['channel']
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await interaction.response.send_message('❌ Ticket refusé. Salon supprimé dans 5 secondes...')
            await asyncio.sleep(5)
            await channel.delete()
        del tickets[self.member_id]

class CloseView(discord.ui.View):
    def __init__(self, member_id):
        super().__init__(timeout=None)
        self.member_id = member_id

    @discord.ui.button(label='🔒 Fermer le ticket', style=discord.ButtonStyle.danger, custom_id='close_ticket')
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message('❌ Tu n\'as pas la permission.', ephemeral=True)
            return

        member = interaction.guild.get_member(self.member_id)
        if member:
            await member.send('🔒 Ton ticket a été **fermé** par le staff.')

        channel_id = tickets[self.member_id]['channel']
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            await interaction.response.send_message('🔒 Ticket fermé. Salon supprimé dans 5 secondes...')
            await asyncio.sleep(5)
            await channel.delete()
        del tickets[self.member_id]

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Membre écrit en MP → envoi au salon staff
    if isinstance(message.channel, discord.DMChannel):
        member_id = message.author.id
        if member_id in tickets and tickets[member_id]['status'] == 'accepted':
            guild = bot.guilds[0]
            channel = guild.get_channel(tickets[member_id]['channel'])
            if channel:
                await channel.send(f'💬 **{message.author.name}** : {message.content}')
        return

    # Staff écrit dans le salon ticket → envoi en MP au membre
    if message.guild:
        for member_id, data in list(tickets.items()):
            if data.get('channel') == message.channel.id and data.get('status') == 'accepted':
                if is_staff(message.author):
                    member = message.guild.get_member(member_id)
                    if member:
                        await member.send(f'👮 **{message.author.name}** : {message.content}')
                break

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    await ctx.send('📩 Clique sur le bouton pour ouvrir un ticket :', view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f'✅ Bot connecté : {bot.user}')

TOKEN = os.getenv('TOKEN')
bot.run(TOKEN)
