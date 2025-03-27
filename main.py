import os
from dotenv import load_dotenv
import discord
import requests
import random
from discord.ext import commands, tasks

# Charger les variables d'environnement
load_dotenv()

# Récupération sécurisée des credentials
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
RIOT_API_KEY = os.getenv('RIOT_API_KEY')
RIOT_REGION = os.getenv('RIOT_REGION', 'americas')
GAME_REGION = os.getenv('GAME_REGION', 'euw1')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))

# Liste d'URLs de gifs
GIFS_LIST = [
    "https://media.tenor.com/B0mcBE69A0sAAAAM/yomi-yuumi.gif",
    "https://media.tenor.com/xcKc5f01qnYAAAAM/sims-cat-yuumi.gif",
    "https://i.redd.it/id48jbzzbknc1.gif",
    "https://media3.giphy.com/media/5BoZ426j1qgl0Ir6EW/200w.gif?cid=6c09b9522waniqqko8y9gvtp89nuymziopcvjymbte0il6ld&ep=v1_gifs_search&rid=200w.gif&ct=g",
    "https://media0.giphy.com/media/To9HIHLOU92iDzfvHX/200w.gif?cid=6c09b9522waniqqko8y9gvtp89nuymziopcvjymbte0il6ld&ep=v1_gifs_search&rid=200w.gif&ct=g"
]

def get_puuid_from_riot_name(riot_name, riot_tag, api_key, region='americas'):
    """
    Récupère le PUUID à partir du nom Riot et du tag
    """
    try:
        url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_name}/{riot_tag}"
        headers = {"X-Riot-Token": api_key}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            account_data = response.json()
            puuid = account_data['puuid']
            print(f"PUUID récupéré pour {riot_name}#{riot_tag}")
            return puuid
        else:
            print(f"Erreur de récupération du PUUID pour {riot_name}#{riot_tag}")
            return None
    
    except Exception as e:
        print(f"Erreur lors de la récupération du PUUID : {e}")
        return None

def get_encrypted_summoner_id(puuid, api_key, region=GAME_REGION):
    """ Récupère l'Encrypted Summoner ID à partir du PUUID """
    try:
        url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        headers = {"X-Riot-Token": api_key}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()['id']
        else:
            print(f"Erreur de récupération du summonerId pour {puuid}")
            return None
    except Exception as e:
        print(f"Erreur lors de la récupération du summonerId : {e}")
        return None

class YuumiTrackerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix='!', intents=intents)
        
        self.yuumi_friends_puuid = []
        self.sent_games = set()  # Pour l'initialisation du message de début de partie
        self.game_stats = {}     # Stocke les stats en cours pour chaque puuid
        
        self.yuumi_roasts = [
            "A défaut d'avoir de la chatte, au moins t'auras un petit chat, bouffon 😹",
            "Le champion qui fait le plus de bruit pour rien… tout ça pour un chat en peluche. 🙄",
            "T'es tellement mauvais, même Yuumi aurait du mal à t'aider. 😂",
            "Tu crois que c'est facile avec Yuumi ? Essaye d'être un vrai champion sans un chat qui te colle ! 🐱",
            "Tu pourrais aussi bien jouer avec un pavé, ça ferait pareil. 😆",
            "Tu penses que Yuumi va te sauver ? Même elle a plus de skill que toi. 🐾",
            "C'est pas un chat, c'est un boulet… et c'est toi qui le traînes. 😏",
            "Dommage que Yuumi ne puisse pas t'apprendre à jouer... C'est la seule chose qu'elle pourrait faire pour toi. 🤣",
            "Si Yuumi est ton champion préféré, c'est sûrement parce que c'est le seul à pouvoir t'attraper. 🐾",
            "Là, même un chat serait plus utile que toi en jeu. 🙃",
            "Tu dois vraiment être nul pour avoir besoin de Yuumi. D'un autre côté, t'as bien l'air d'un bouffon. 🧸"
        ]
    
    def add_friend(self, riot_name, riot_tag):
        puuid = get_puuid_from_riot_name(riot_name, riot_tag, RIOT_API_KEY, RIOT_REGION)
        if puuid:
            self.yuumi_friends_puuid.append(puuid)
            print(f"Ajout de {riot_name}#{riot_tag} avec PUUID: {puuid}")
        else:
            print(f"Impossible d'ajouter {riot_name}#{riot_tag}")

    async def check_current_game(self, puuid):
        """
        Vérifie si l'ami est en partie et retourne un tuple :
        (is_yuumi_game, summoner_name, game_id, stats)
        stats est un dictionnaire avec 'kills', 'assists', 'deaths'
        """
        try:
            summoner_url = f"https://{GAME_REGION}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
            headers = {"X-Riot-Token": RIOT_API_KEY}
            summoner_response = requests.get(summoner_url, headers=headers)

            if summoner_response.status_code != 200:
                print(f"Erreur récupération SummonerId : {summoner_response.status_code} - {summoner_response.text}")
                return False, "", None, {}

            summoner_data = summoner_response.json()
            # On n'utilise plus encrypted_summoner_id ici puisque l'API Spectator se base sur le puuid

            url = f"https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}?api_key={RIOT_API_KEY}"
            response = requests.get(url)

            if response.status_code == 200:
                game_data = response.json()
                for participant in game_data['participants']:
                    if participant['championId'] == 350:  # Yuumi = 350
                        game_id = game_data['gameId']
                        # Récupération des statistiques (on suppose que ces champs existent)
                        participant_stats = {
                            'kills': participant.get('kills', 0),
                            'assists': participant.get('assists', 0),
                            'deaths': participant.get('deaths', 0)
                        }
                        return True, participant['riotId'], game_id, participant_stats
            else:
                print(f"Pas de partie en cours pour {puuid}. Code {response.status_code}")
            
            return False, "", None, {}

        except Exception as e:
            print(f"Erreur lors de la vérification de la partie en cours : {e}")
            return False, "", None, {}

    @tasks.loop(minutes=1)
    async def track_yuumi_games(self):
        channel = self.get_channel(CHANNEL_ID)
        
        for puuid in self.yuumi_friends_puuid:
            is_yuumi_game, summoner_name, game_id, stats = await self.check_current_game(puuid)
            if is_yuumi_game and game_id:
                # Si c'est une nouvelle partie ou si le game_id a changé, initialiser
                if (puuid not in self.game_stats) or (self.game_stats[puuid]['game_id'] != game_id):
                    self.game_stats[puuid] = {
                        'game_id': game_id,
                        'kills': stats.get('kills', 0),
                        'assists': stats.get('assists', 0),
                        'deaths': stats.get('deaths', 0)
                    }
                    # Envoyer le message d'annonce de la partie si ce n'est pas déjà fait
                    if game_id not in self.sent_games:
                        roast = random.choice(self.yuumi_roasts)
                        gif_url = random.choice(GIFS_LIST)
                        
                        embed = discord.Embed(
                            title=f"{summoner_name} joue Yuumi !",
                            description=f"{roast}\n**C'est l'heure de la moquerie !**",
                            color=discord.Color.purple()
                        )
                        embed.set_image(url=gif_url)
                        embed.set_footer(text="L'équipe Yuumi vous observe 👀")
                        
                        await channel.send(f"**{summoner_name}**, tu es en train de jouer Yuumi !", embed=embed)
                        self.sent_games.add(game_id)
                else:
                    # Partie en cours : comparer les stats et envoyer des messages pour chaque nouveau kill/assist/death
                    prev_stats = self.game_stats[puuid]
                    
                    new_kills = stats.get('kills', 0) - prev_stats.get('kills', 0)
                    new_assists = stats.get('assists', 0) - prev_stats.get('assists', 0)
                    new_deaths = stats.get('deaths', 0) - prev_stats.get('deaths', 0)
                    
                    for _ in range(new_kills):
                        await channel.send(f"**{summoner_name}**: don't steal kills yuumi, you've been a bad support!")
                    for _ in range(new_assists):
                        await channel.send(f"**{summoner_name}**: good job yuumi, you've been a good support!")
                    for _ in range(new_deaths):
                        await channel.send(f"**{summoner_name}**: i hope you gave everything to save your ADC!")
                    
                    # Mettre à jour les stats
                    self.game_stats[puuid].update({
                        'kills': stats.get('kills', 0),
                        'assists': stats.get('assists', 0),
                        'deaths': stats.get('deaths', 0)
                    })
            else:
                # Si le joueur n'est plus en partie, on retire ses stats de suivi
                if puuid in self.game_stats:
                    del self.game_stats[puuid]

    async def on_ready(self):
        print(f'Connecté en tant que {self.user}')
        self.add_friend('Taki', 'hupp')
        self.add_friend('Tel', 'zzzzz')
        self.add_friend('wati bidon', 'euw')
        self.add_friend('Frootz', 'VIPER')
        self.track_yuumi_games.start()

def main():
    # Vérification de la présence des variables d'environnement essentielles
    if not DISCORD_TOKEN or not RIOT_API_KEY:
        print("Erreur : Les tokens Discord et Riot sont requis. Vérifiez votre fichier .env")
        return
    
    bot = YuumiTrackerBot()
    bot.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()