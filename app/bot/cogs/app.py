from pickle import FALSE
import app.bot.helper.jellyfinhelper as jelly
from app.bot.helper.textformat import bcolors
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer
import app.bot.helper.db as db
import app.bot.helper.plexhelper as plexhelper
import app.bot.helper.jellyfinhelper as jelly
import texttable
from app.bot.helper.message import *
from app.bot.helper.confighelper import *

CONFIG_PATH = 'app/config/config.ini'
BOT_SECTION = 'bot_envs'

plex_configured = True
jellyfin_configured = True

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

plex_token_configured = True
try:
    PLEX_TOKEN = config.get(BOT_SECTION, 'plex_token')
    PLEX_BASE_URL = config.get(BOT_SECTION, 'plex_base_url')
except:
    print("Nu s-au găsit detalii despre tokenul de autentificare Plex")
    plex_token_configured = False

# Get Plex config
try:
    PLEXUSER = config.get(BOT_SECTION, 'plex_user')
    PLEXPASS = config.get(BOT_SECTION, 'plex_pass')
    PLEX_SERVER_NAME = config.get(BOT_SECTION, 'plex_server_name')
except:
    print("Nu s-au găsit informații de conectare Plex")
    if not plex_token_configured:
        print("Nu s-a putut încărca configurația plex")
        plex_configured = False

# Get Plex roles config
try:
    plex_roles = config.get(BOT_SECTION, 'plex_roles')
except:
    plex_roles = None
if plex_roles:
    plex_roles = list(plex_roles.split(','))
else:
    plex_roles = []

# Get Plex libs config
try:
    Plex_LIBS = config.get(BOT_SECTION, 'plex_libs')
except:
    Plex_LIBS = None
if Plex_LIBS is None:
    Plex_LIBS = ["all"]
else:
    Plex_LIBS = list(Plex_LIBS.split(','))
    
# Get Jellyfin config
try:
    JELLYFIN_SERVER_URL = config.get(BOT_SECTION, 'jellyfin_server_url')
    JELLYFIN_API_KEY = config.get(BOT_SECTION, "jellyfin_api_key")
except:
    jellyfin_configured = False

# Get Jellyfin roles config
try:
    jellyfin_roles = config.get(BOT_SECTION, 'jellyfin_roles')
except:
    jellyfin_roles = None
if jellyfin_roles:
    jellyfin_roles = list(jellyfin_roles.split(','))
else:
    jellyfin_roles = []

# Get Jellyfin libs config
try:
    jellyfin_libs = config.get(BOT_SECTION, 'jellyfin_libs')
except:
    jellyfin_libs = None
if jellyfin_libs is None:
    jellyfin_libs = ["all"]
else:
    jellyfin_libs = list(jellyfin_libs.split(','))

# Get Enable config
try:
    USE_JELLYFIN = config.get(BOT_SECTION, 'jellyfin_enabled')
    USE_JELLYFIN = USE_JELLYFIN.lower() == "true"
except:
    USE_JELLYFIN = False

try:
    USE_PLEX = config.get(BOT_SECTION, "plex_enabled")
    USE_PLEX = USE_PLEX.lower() == "true"
except:
    USE_PLEX = False

try:
    JELLYFIN_EXTERNAL_URL = config.get(BOT_SECTION, "jellyfin_external_url")
    if not JELLYFIN_EXTERNAL_URL:
        JELLYFIN_EXTERNAL_URL = JELLYFIN_SERVER_URL
except:
    JELLYFIN_EXTERNAL_URL = JELLYFIN_SERVER_URL
    print("Nu s-a putut obține adresa URL externă Jellyfin. Implicit la adresa URL a serverului.")

if USE_PLEX and plex_configured:
    try:
        print("Conectare la Plex......")
        if plex_token_configured and PLEX_TOKEN and PLEX_BASE_URL:
            print("Folosind tokenul de autentificare Plex")
            plex = PlexServer(PLEX_BASE_URL, PLEX_TOKEN)
        else:
            print("Folosind informațiile de conectare Plex")
            account = MyPlexAccount(PLEXUSER, PLEXPASS)
            plex = account.resource(PLEX_SERVER_NAME).connect()  # returns a PlexServer instance
        print('Conectat la plex!')
    except Exception as e:
        # probably rate limited.
        print('Eroare la autentificarea plex. Vă rugăm să verificați detaliile de autentificare Plex. Dacă ați repornit botul de mai multe ori recent, cel mai probabil acest lucru se datorează faptului că rata este limitată pe API-ul Plex. Încercați din nou peste 10 minute.')
        print(f'Eroare: {e}')
else:
    print(f"Plex {'disabled' if not USE_PLEX else 'not configured'}. Sari peste autentificarea Plex.")


class app(commands.Cog):
    # App command groups
    plex_commands = app_commands.Group(name="plex", description="Membarr Plex commands")
    jellyfin_commands = app_commands.Group(name="jellyfin", description="Membarr Jellyfin commands")
    membarr_commands = app_commands.Group(name="membarr", description="Membarr general commands")

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print("{:^41}".format(f"MEMBARR V {MEMBARR_VERSION}"))
        print(f'Made by Yoruio https://github.com/Yoruio/\n')
        print(f'Forked from Invitarr https://github.com/Sleepingpirates/Invitarr')
        print(f'Named by lordfransie')
        print(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        print('------')

        # TODO: Make these debug statements work. roles are currently empty arrays if no roles assigned.
        if plex_roles is None:
            print('Configurați rolurile Plex pentru a activa invitarea automată la Plex după ce este atribuit un rol.')
        if jellyfin_roles is None:
            print('Configurați rolurile Jellyfin pentru a activa invitarea automată la Jellyfin după ce este atribuit un rol.')
    
    async def getemail(self, after):
        email = None
        await embedinfo(after,'Bun venit la '+ PLEX_SERVER_NAME +'. Vă rugăm să răspundeți cu e-mailul pentru a fi adăugat la serverul Plex!')
        await embedinfo(after,'Dacă nu răspundeți în 24 de ore, cererea va fi anulată, iar administratorul serverului va trebui să vă adauge manual.')
        while(email == None):
            def check(m):
                return m.author == after and not m.guild
            try:
                email = await self.bot.wait_for('message', timeout=86400, check=check)
                if(plexhelper.verifyemail(str(email.content))):
                    return str(email.content)
                else:
                    email = None
                    message = "E-mailul pe care l-ați furnizat este nevalid, vă rugăm să răspundeți numai cu e-mailul pe care l-ați folosit pentru a vă înscrie la Plex."
                    await embederror(after, message)
                    continue
            except asyncio.TimeoutError:
                message = "Timp expirat. Vă rugăm să contactați direct administratorul serverului."
                await embederror(after, message)
                return None
    
    async def getusername(self, after):
        username = None
        await embedinfo(after, f"Bun venit la Jellyfin! Vă rugăm să răspundeți cu numele dvs. de utilizator dorit pentru a fi adăugat pe serverul Jellyfin!")
        await embedinfo(after, f"Dacă nu răspundeți în 24 de ore, cererea va fi anulată, iar administratorul serverului va trebui să vă adauge manual.")
        while (username is None):
            def check(m):
                return m.author == after and not m.guild
            try:
                username = await self.bot.wait_for('message', timeout=86400, check=check)
                if(jelly.verify_username(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, str(username.content))):
                    return str(username.content)
                else:
                    username = None
                    message = "Acest nume de utilizator este deja ales. Vă rugăm să selectați un alt nume de utilizator."
                    await embederror(after, message)
                    continue
            except asyncio.TimeoutError:
                message = "Timp expirat. Vă rugăm să contactați direct administratorul serverului."
                print("Solicitarea utilizatorului Jellyfin a expirat")
                await embederror(after, message)
                return None
            except Exception as e:
                await embederror(after, "Ceva a mers prost. Vă rugăm să încercați din nou cu un alt nume de utilizator.")
                print (e)
                username = None


    async def addtoplex(self, email, response):
        if(plexhelper.verifyemail(email)):
            if plexhelper.plexadd(plex,email,Plex_LIBS):
                await embedinfo(response, 'Această adresă de e-mail a fost adăugată la plex')
                return True
            else:
                await embederror(response, 'A apărut o eroare la adăugarea acestei adrese de e-mail. Verificați jurnalele.')
                return False
        else:
            await embederror(response, 'E-mail nevalid.')
            return False

    async def removefromplex(self, email, response):
        if(plexhelper.verifyemail(email)):
            if plexhelper.plexremove(plex,email):
                await embedinfo(response, 'Această adresă de e-mail a fost eliminată din plex.')
                return True
            else:
                await embederror(response, 'A apărut o eroare la eliminarea acestei adrese de e-mail. Verificați jurnalele.')
                return False
        else:
            await embederror(response, 'E-mail nevalid.')
            return False
    
    async def addtojellyfin(self, username, password, response):
        if not jelly.verify_username(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username):
            await embederror(response, f'Un cont cu numele de utilizator {username} deja există.')
            return False

        if jelly.add_user(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username, password, jellyfin_libs):
            return True
        else:
            await embederror(response, 'A apărut o eroare la adăugarea acestui utilizator la Jellyfin. Verificați jurnalele pentru mai multe informații.')
            return False

    async def removefromjellyfin(self, username, response):
        if jelly.verify_username(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username):
            await embederror(response, f'Nu s-a putut găsi contul cu numele de utilizator {username}.')
            return
        
        if jelly.remove_user(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username):
            await embedinfo(response, f'Utilizator eliminat cu succes {username} din Jellyfin.')
            return True
        else:
            await embederror(response, f'A apărut o eroare la eliminarea acestui utilizator din Jellyfin. Verificați jurnalele pentru mai multe informații.')
            return False

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if plex_roles is None and jellyfin_roles is None:
            return
        roles_in_guild = after.guild.roles
        role = None

        plex_processed = False
        jellyfin_processed = False

        # Check Plex roles
        if plex_configured and USE_PLEX:
            for role_for_app in plex_roles:
                for role_in_guild in roles_in_guild:
                    if role_in_guild.name == role_for_app:
                        role = role_in_guild

                    # Plex role was added
                    if role is not None and (role in after.roles and role not in before.roles):
                        email = await self.getemail(after)
                        if email is not None:
                            await embedinfo(after, "Am înțeles, vă vom adăuga e-mailul la plex în curând!")
                            if plexhelper.plexadd(plex,email,Plex_LIBS):
                                db.save_user_email(str(after.id), email)
                                await asyncio.sleep(5)
                                await embedinfo(after, 'Ai fost adăugat la Plex! Conectați-vă la plex și acceptați invitația!')
                            else:
                                await embedinfo(after, 'A apărut o eroare la adăugarea acestei adrese de e-mail. Contactați Administratorul.')
                        plex_processed = True
                        break

                    # Plex role was removed
                    elif role is not None and (role not in after.roles and role in before.roles):
                        try:
                            user_id = after.id
                            email = db.get_useremail(user_id)
                            plexhelper.plexremove(plex,email)
                            deleted = db.remove_email(user_id)
                            if deleted:
                                print("E-mailul Plex a fost eliminat {} din db".format(after.name))
                                #await secure.send(plexname + ' ' + after.mention + ' a fost șters din plex')
                            else:
                                print("Nu se poate elimina Plex de la acest utilizator.")
                            await embedinfo(after, "Ai fost eliminat din Plex")
                        except Exception as e:
                            print(e)
                            print("{} Nu se poate elimina acest utilizator din plex.".format(email))
                        plex_processed = True
                        break
                if plex_processed:
                    break

        role = None
        # Check Jellyfin roles
        if jellyfin_configured and USE_JELLYFIN:
            for role_for_app in jellyfin_roles:
                for role_in_guild in roles_in_guild:
                    if role_in_guild.name == role_for_app:
                        role = role_in_guild

                    # Jellyfin role was added
                    if role is not None and (role in after.roles and role not in before.roles):
                        print("Rolul Jellyfin adăugat")
                        username = await self.getusername(after)
                        print("Nume de utilizator preluat de la utilizator")
                        if username is not None:
                            await embedinfo(after, "Am înțeles, vă vom crea contul Jellyfin în curând!")
                            password = jelly.generate_password(16)
                            if jelly.add_user(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username, password, jellyfin_libs):
                                db.save_user_jellyfin(str(after.id), username)
                                await asyncio.sleep(5)
                                await embedcustom(after, "Ai fost adăugat la Jellyfin!", {'Utilizator': username, 'Parolă': f"||{password}||"})
                                await embedinfo(after, f"Dute la {JELLYFIN_EXTERNAL_URL} pentru a te autentifica!")
                            else:
                                await embedinfo(after, 'A apărut o eroare la adăugarea acestui utilizator la Jellyfin. Contactează Administratorul.')
                        jellyfin_processed = True
                        break

                    # Jellyfin role was removed
                    elif role is not None and (role not in after.roles and role in before.roles):
                        print("Rolul Jellyfin eliminat")
                        try:
                            user_id = after.id
                            username = db.get_jellyfin_username(user_id)
                            jelly.remove_user(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, username)
                            deleted = db.remove_jellyfin(user_id)
                            if deleted:
                                print("A eliminat Jellyfin din {}".format(after.name))
                                #await secure.send(plexname + ' ' + after.mention + ' a fost scos din plex')
                            else:
                                print("Nu se poate elimina Jellyfin de la acest utilizator")
                            await embedinfo(after, "Ai fost eliminat din Jellyfin")
                        except Exception as e:
                            print(e)
                            print("{} Nu se poate elimina acest utilizator din Jellyfin.".format(username))
                        jellyfin_processed = True
                        break
                if jellyfin_processed:
                    break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if USE_PLEX and plex_configured:
            email = db.get_useremail(member.id)
            plexhelper.plexremove(plex,email)
        
        if USE_JELLYFIN and jellyfin_configured:
            jellyfin_username = db.get_jellyfin_username(member.id)
            jelly.remove_user(JELLYFIN_SERVER_URL, JELLYFIN_API_KEY, jellyfin_username)
            
        deleted = db.delete_user(member.id)
        if deleted:
            print("Eliminat {} de la db pentru că utilizatorul a părăsit serverul Discord.".format(email))

    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="invite", description="Invitați un utilizator la Plex")
    async def plexinvite(self, interaction: discord.Interaction, email: str):
        await self.addtoplex(email, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @plex_commands.command(name="remove", description="Eliminați un utilizator din Plex")
    async def plexremove(self, interaction: discord.Interaction, email: str):
        await self.removefromplex(email, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @jellyfin_commands.command(name="invite", description="Invitați un utilizator la Jellyfin")
    async def jellyfininvite(self, interaction: discord.Interaction, username: str):
        password = jelly.generate_password(16)
        if await self.addtojellyfin(username, password, interaction.response):
            await embedcustom(interaction.response, "Utilizator Jellyfin creat!", {'Utilizator': username, 'Parola': f"||{password}||"})

    @app_commands.checks.has_permissions(administrator=True)
    @jellyfin_commands.command(name="remove", description="Eliminați un utilizator din Jellyfin")
    async def jellyfinremove(self, interaction: discord.Interaction, username: str):
        await self.removefromjellyfin(username, interaction.response)
    
    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbadd", description="Adăugați un utilizator la baza de date Membarr")
    async def dbadd(self, interaction: discord.Interaction, member: discord.Member, email: str = "", jellyfin_username: str = ""):
        email = email.strip()
        jellyfin_username = jellyfin_username.strip()
        
        # Check email if provided
        if email and not plexhelper.verifyemail(email):
            await embederror(interaction.response, "E-mail nevalid.")
            return

        try:
            db.save_user_all(str(member.id), email, jellyfin_username)
            await embedinfo(interaction.response,'Utilizatorul a fost adăugat la baza de date.')
        except Exception as e:
            await embedinfo(interaction.response, 'A apărut o eroare la adăugarea acestui utilizator la baza de date. Verificați jurnalele Membarr pentru mai multe informații')
            print(e)

    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbls", description="Vizualizați baza de date Membarr")
    async def dbls(self, interaction: discord.Interaction):

        embed = discord.Embed(title='Baza de Date Membarr.')
        all = db.read_all()
        table = texttable.Texttable()
        table.set_cols_dtype(["t", "t", "t", "t"])
        table.set_cols_align(["c", "c", "c", "c"])
        header = ("#", "Name", "Email", "Jellyfin")
        table.add_row(header)
        for index, peoples in enumerate(all):
            index = index + 1
            id = int(peoples[1])
            dbuser = self.bot.get_user(id)
            dbemail = peoples[2] if peoples[2] else "Fără Plex"
            dbjellyfin = peoples[3] if peoples[3] else "Fără Jellyfin"
            try:
                username = dbuser.name
            except:
                username = "Utilizatorul nu a fost găsit."
            embed.add_field(name=f"**{index}. {username}**", value=dbemail+'\n'+dbjellyfin+'\n', inline=False)
            table.add_row((index, username, dbemail, dbjellyfin))
        
        total = str(len(all))
        if(len(all)>25):
            f = open("db.txt", "w")
            f.write(table.draw())
            f.close()
            await interaction.response.send_message("Baza de date prea mare! Total: {total}".format(total = total),file=discord.File('db.txt'), ephemeral=True)
        else:
            await interaction.response.send_message(embed = embed, ephemeral=True)
        
            
    @app_commands.checks.has_permissions(administrator=True)
    @membarr_commands.command(name="dbrm", description="Eliminați utilizatorul din baza de date Membarr")
    async def dbrm(self, interaction: discord.Interaction, position: int):
        embed = discord.Embed(title='Baza de Date Membarr.')
        all = db.read_all()
        for index, peoples in enumerate(all):
            index = index + 1
            id = int(peoples[1])
            dbuser = self.bot.get_user(id)
            dbemail = peoples[2] if peoples[2] else "Fără Plex"
            dbjellyfin = peoples[3] if peoples[3] else "Fără Jellyfin"
            try:
                username = dbuser.name
            except:
                username = "Utilizatorul nu a fost găsit."
            embed.add_field(name=f"**{index}. {username}**", value=dbemail+'\n'+dbjellyfin+'\n', inline=False)

        try:
            position = int(position) - 1
            id = all[position][1]
            discord_user = await self.bot.fetch_user(id)
            username = discord_user.name
            deleted = db.delete_user(id)
            if deleted:
                print("Eliminat {} din baza de date".format(username))
                await embedinfo(interaction.response,"Eliminat {} din baza de date".format(username))
            else:
                await embederror(interaction.response,"Nu se poate elimina acest utilizator din db.")
        except Exception as e:
            print(e)

async def setup(bot):
    await bot.add_cog(app(bot))
