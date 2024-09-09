from pydoc import describe
import discord
import os
from discord.ext import commands, tasks
from discord.utils import get
from discord.ui import Button, View, Select
from discord import app_commands
import asyncio
import sys
from app.bot.helper.confighelper import MEMBARR_VERSION, switch, Discord_bot_token, plex_roles, jellyfin_roles
import app.bot.helper.confighelper as confighelper
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.message import *
from requests import ConnectTimeout
from plexapi.myplex import MyPlexAccount

maxroles = 10

if switch == 0:
    print("Config lipsă.")
    sys.exit()


class Bot(commands.Bot):
    def __init__(self) -> None:
        print("Se inițializează botul Discord")
        intents = discord.Intents.all()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=".", intents=intents)

    async def on_ready(self):
        print("Botul este online.")
        for guild in self.guilds:
            print("Sincronizarea comenzilor cu " + guild.name)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_guild_join(self, guild):
        print(f"S-a alăturat breaslei {guild.name}")
        print(f"Sincronizarea comenzilor cu {guild.name}")
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)

    async def setup_hook(self):
        print("Se încarcă conectorii serverului media")
        await self.load_extension(f'app.bot.cogs.app')


bot = Bot()


async def reload():
    await bot.reload_extension(f'app.bot.cogs.app')


async def getuser(interaction, server, type):
    value = None
    await interaction.user.send("Vă rugăm să răspundeți cu {} {}:".format(server, type))
    while (value == None):
        def check(m):
            return m.author == interaction.user and not m.guild

        try:
            value = await bot.wait_for('message', timeout=200, check=check)
            return value.content
        except asyncio.TimeoutError:
            message = "Timp expirat. Încearcă din nou."
            return None


plex_commands = app_commands.Group(name="plexsettings", description="Comenzi Membarr Plex")
jellyfin_commands = app_commands.Group(name="jellyfinsettings", description="Comenzi Membarr Jellyfin")


@plex_commands.command(name="addrole", description="Adăugați un rol pentru a adăuga automat utilizatori la Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(plex_roles) <= maxroles:
        # Do not add roles multiple times.
        if role.name in plex_roles:
            await embederror(interaction.response, f"Rolul Plex \"{role.name}\" deja adăugat.")
            return

        plex_roles.append(role.name)
        saveroles = ",".join(plex_roles)
        confighelper.change_config("plex_roles", saveroles)
        await interaction.response.send_message("Roluri Plex actualizate. Botul se repornește. Va rugam asteptati.", ephemeral=True)
        print("Rolurile Plex au fost actualizate. Se repornește bot, dă-i câteva secunde.")
        await reload()
        print("Botul a fost repornit. Dă-i câteva secunde.")


@plex_commands.command(name="removerole", description="Nu mai adăugați utilizatori cu un rol la Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in plex_roles:
        await embederror(interaction.response, f"\"{role.name}\" în prezent nu este un rol Plex.")
        return
    plex_roles.remove(role.name)
    confighelper.change_config("plex_roles", ",".join(plex_roles))
    await interaction.response.send_message(f"Membarr va opri adăugarea automată \"{role.name}\" la Plex", ephemeral=True)


@plex_commands.command(name="listroles", description="Listați toate rolurile ai căror membri vor fi adăugați automat la Plex")
@app_commands.checks.has_permissions(administrator=True)
async def plexrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Următoarele roluri sunt adăugate automat la Plex:\n" +
        ", ".join(plex_roles), ephemeral=True
    )


@plex_commands.command(name="setup", description="Configurați integrarea Plex")
@app_commands.checks.has_permissions(administrator=True)
async def setupplex(interaction: discord.Interaction, username: str, password: str, server_name: str,
                    base_url: str = "", save_token: bool = True):
    await interaction.response.defer()
    try:
        account = MyPlexAccount(username, password)
        plex = account.resource(server_name).connect()
    except Exception as e:
        if str(e).startswith("(429)"):
            await embederror(interaction.followup, "Prea multe cereri. Vă rugăm să încercați din nou mai târziu.")
            return

        await embederror(interaction.followup, "Nu s-a putut conecta la serverul Plex. Vă rugăm să vă verificați acreditările.")
        return

    if (save_token):
        # Save new config entries
        confighelper.change_config("plex_base_url", plex._baseurl if base_url == "" else base_url)
        confighelper.change_config("plex_token", plex._token)
        confighelper.change_config("plex_server_name", server_name)

        # Delete old config entries
        confighelper.change_config("plex_user", "")
        confighelper.change_config("plex_pass", "")
    else:
        # Save new config entries
        confighelper.change_config("plex_user", username)
        confighelper.change_config("plex_pass", password)
        confighelper.change_config("plex_server_name", server_name)

        # Delete old config entries
        confighelper.change_config("plex_base_url", "")
        confighelper.change_config("plex_token", "")

    print("Detaliile de autentificare Plex au fost actualizate. Se repornește bot.")
    await interaction.followup.send(
        "Detaliile de autentificare Plex au fost actualizate. Se repornește bot. Va rugam asteptati.\n" +
        "Vă rugăm să verificați jurnalele și să vă asigurați că vedeți linia: `Autentificat in plex`. Dacă nu rulați această comandă din nou și asigurați-vă că introduceți valorile corecte.",
        ephemeral=True
    )
    await reload()
    print("Botul a fost repornit. Dă-i câteva secunde.")


@jellyfin_commands.command(name="addrole", description="Adăugați un rol pentru a adăuga automat utilizatori la Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleadd(interaction: discord.Interaction, role: discord.Role):
    if len(jellyfin_roles) <= maxroles:
        # Do not add roles multiple times.
        if role.name in jellyfin_roles:
            await embederror(interaction.response, f"Rolul Jellyfin \"{role.name}\" deja adăugat.")
            return

        jellyfin_roles.append(role.name)
        saveroles = ",".join(jellyfin_roles)
        confighelper.change_config("jellyfin_roles", saveroles)
        await interaction.response.send_message("Roluri Jellyfin actualizate. Botul se repornește. Vă rugăm să așteptați câteva secunde.",
                                                ephemeral=True)
        print("Roluri Jellyfin actualizate. Se repornește bot.")
        await reload()
        print("Botul a fost repornit. Dă-i câteva secunde.")


@jellyfin_commands.command(name="removerole", description="Nu mai adăugați utilizatori cu un rol la Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyroleremove(interaction: discord.Interaction, role: discord.Role):
    if role.name not in jellyfin_roles:
        await embederror(interaction.response, f"\"{role.name}\" în prezent nu este un rol Jellyfin.")
        return
    jellyfin_roles.remove(role.name)
    confighelper.change_config("jellyfin_roles", ",".join(jellyfin_roles))
    await interaction.response.send_message(f"Membarr va opri adăugarea automată \"{role.name}\" la Jellyfin",
                                            ephemeral=True)


@jellyfin_commands.command(name="listroles",
                           description="Listați toate rolurile ai căror membri vor fi adăugați automat la Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def jellyrolels(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Următoarele roluri sunt adăugate automat la Jellyfin:\n" +
        ", ".join(jellyfin_roles), ephemeral=True
    )


@jellyfin_commands.command(name="setup", description="Configurați integrarea Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def setupjelly(interaction: discord.Interaction, server_url: str, api_key: str, external_url: str = None):
    await interaction.response.defer()
    # get rid of training slashes
    server_url = server_url.rstrip('/')

    try:
        server_status = jelly.get_status(server_url, api_key)
        if server_status == 200:
            pass
        elif server_status == 401:
            # Unauthorized
            await embederror(interaction.followup, "Cheia API furnizată este nevalidă")
            return
        elif server_status == 403:
            # Forbidden
            await embederror(interaction.followup, "Cheia API furnizată nu are permisiuni")
            return
        elif server_status == 404:
            # page not found
            await embederror(interaction.followup, "Punctul final al serverului furnizat nu a fost găsit")
            return
        else:
            await embederror(interaction.followup,
                             "A apărut o eroare necunoscută la conectarea la Jellyfin. Verificați jurnalele Membarr.")
    except ConnectTimeout as e:
        await embederror(interaction.followup,
                         "Conexiunea la server a expirat. Verificați dacă Jellyfin este online și accesibil.")
        return
    except Exception as e:
        print("Excepție la testarea conexiunii Jellyfin")
        print(type(e).__name__)
        print(e)
        await embederror(interaction.followup, "Excepție necunoscută în timpul conectării la Jellyfin. Verificați jurnalele Membarr")
        return

    confighelper.change_config("jellyfin_server_url", str(server_url))
    confighelper.change_config("jellyfin_api_key", str(api_key))
    if external_url is not None:
        confighelper.change_config("jellyfin_external_url", str(external_url))
    else:
        confighelper.change_config("jellyfin_external_url", "")
    print("Adresa URL a serverului Jellyfin și cheia API au fost actualizate. Se repornește bot.")
    await interaction.followup.send("Adresa URL a serverului Jellyfin și cheia API au fost actualizate. Se repornește bot.", ephemeral=True)
    await reload()
    print("Botul a fost repornit. Dă-i câteva secunde.")


@plex_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupplexlibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
        confighelper.change_config("plex_libs", str(libraries))
        print("Plex libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message("Plex libraries updated. Please wait a few seconds for bot to restart.",
                                                ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


@jellyfin_commands.command(name="setuplibs", description="Setup libraries that new users can access")
@app_commands.checks.has_permissions(administrator=True)
async def setupjellylibs(interaction: discord.Interaction, libraries: str):
    if not libraries:
        await embederror(interaction.response, "libraries string is empty.")
        return
    else:
        # Do some fancy python to remove spaces from libraries string, but only where wanted.
        libraries = ",".join(list(map(lambda lib: lib.strip(), libraries.split(","))))
        confighelper.change_config("jellyfin_libs", str(libraries))
        print("Jellyfin libraries updated. Restarting bot. Please wait.")
        await interaction.response.send_message(
            "Jellyfin libraries updated. Please wait a few seconds for bot to restart.", ephemeral=True)
        await reload()
        print("Bot has been restarted. Give it a few seconds.")


# Enable / Disable Plex integration
@plex_commands.command(name="enable", description="Enable auto-adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def enableplex(interaction: discord.Interaction):
    if confighelper.USE_PLEX:
        await interaction.response.send_message("Plex already enabled.", ephemeral=True)
        return
    confighelper.change_config("plex_enabled", True)
    print("Plex enabled, reloading server")
    await reload()
    confighelper.USE_PLEX = True
    await interaction.response.send_message("Plex enabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@plex_commands.command(name="disable", description="Disable adding users to Plex")
@app_commands.checks.has_permissions(administrator=True)
async def disableplex(interaction: discord.Interaction):
    if not confighelper.USE_PLEX:
        await interaction.response.send_message("Plex already disabled.", ephemeral=True)
        return
    confighelper.change_config("plex_enabled", False)
    print("Plex disabled, reloading server")
    await reload()
    confighelper.USE_PLEX = False
    await interaction.response.send_message("Plex disabled. Restarting server. Give it a few seconds.", ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


# Enable / Disable Jellyfin integration
@jellyfin_commands.command(name="enable", description="Enable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def enablejellyfin(interaction: discord.Interaction):
    if confighelper.USE_JELLYFIN:
        await interaction.response.send_message("Jellyfin already enabled.", ephemeral=True)
        return
    confighelper.change_config("jellyfin_enabled", True)
    print("Jellyfin enabled, reloading server")
    confighelper.USE_JELLYFIN = True
    await reload()
    await interaction.response.send_message("Jellyfin enabled. Restarting server. Give it a few seconds.",
                                            ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


@jellyfin_commands.command(name="disable", description="Disable adding users to Jellyfin")
@app_commands.checks.has_permissions(administrator=True)
async def disablejellyfin(interaction: discord.Interaction):
    if not confighelper.USE_JELLYFIN:
        await interaction.response.send_message("Jellyfin already disabled.", ephemeral=True)
        return
    confighelper.change_config("jellyfin_enabled", False)
    print("Jellyfin disabled, reloading server")
    await reload()
    confighelper.USE_JELLYFIN = False
    await interaction.response.send_message("Jellyfin disabled. Restarting server. Give it a few seconds.",
                                            ephemeral=True)
    print("Bot has restarted. Give it a few seconds.")


bot.tree.add_command(plex_commands)
bot.tree.add_command(jellyfin_commands)

bot.run(Discord_bot_token)
