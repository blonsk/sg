import json
import os
import itertools
import collections
import re
import pandas as pd

class matcher:
    def __init__(self, nickname_file_path):        
        self.name2nick = self.parse_nickname_file(nickname_file_path)

    
    def match_email_name(self, email, first_name, last_name):
        # Remove digits from the email
        # Ex: john.smith453@gmail.com
        email_pre = self.preprocess_email(email)
        if email_pre == '' or first_name == '' or last_name == '':
            return None
        '''
        if self.filtered_names:
            if email_pre in self.filtered_names:
                return None
        '''
        fname = first_name.lower()
        lname = last_name.lower()

        # Case: name parts are separated by '.' or '_'
        # Example: john.smith, j.smith, smith.j, john.s, s.john, 
        #          john_smith, j_smith, smith_j, john_s, s_john
        separators = ['.', '_']
        for sep in separators:
            parts = email_pre.split(sep)
            if len(parts) > 1:
                # Try all combinations of parts separated by a dot, and take minimum score
                scores = [self.match_name_parts(fname, lname, part1, part2)
                          for part1, part2 in list(itertools.combinations(parts, 2))]
                scores = [score for score in scores if score is not None]
                if len(scores):
                    argmin = np.argmin([a[0] for a in scores])
                    return scores[argmin][0], f'Name parts separated by a "{sep}"|{scores[argmin][1]}'
                return None
        
        # If name parts are NOT separated by dot or _
        else:
            # Case: 1st char of first name then last name, or 1st char of last name then first name
            # Ex: jsmith of sjohn
            part1 = email_pre[0]
            part2 = email_pre[1:]
            score1 = self.match_name_parts(fname, lname, part1, part2)
            if score1: score1 = (score1[0], f'First char of first/last-name then first/last-name|{score1[1]}')

            # Case: first name then first char of last name, or last name then first char of first name
            # Ex: johns of smithj
            part1 = email_pre[:-1]
            part2 = email_pre[-1]
            score2 = self.match_name_parts(fname, lname, part1, part2)
            if score2: score2 = (score2[0], f'First/last-name then first char of first/last-name|{score2[1]}')

            # Case: 1st 2 chars of first name then last name, or 1st 2 chars of last name then first name
            # Ex: josmith of smjohn
            part1 = email_pre[:2]
            part2 = email_pre[2:]
            score7 = self.match_name_parts(fname, lname, part1, part2)
            if score7: score7 = (score7[0], f'First 2 chars of first/last-name then first/last-name|{score7[1]}')

            # Case: first name then first char of last name, or last name then first 2 chars of first name
            # Ex: johnsm of smithjo
            part1 = email_pre[:-2]
            part2 = email_pre[-2:]
            score8 = self.match_name_parts(fname, lname, part1, part2)
            if score8: score8 = (score8[0], f'First/last-name then first 2 chars of first/last-name|{score8[1]}')

            # Case: only first name. Add a penalty of 5 for missing last name
            # Ex: john
            score3 = self.match_first_name(fname, email_pre)
            if score3: score3 = (score3[0] + 5, f'Only first name|{score3[1]}')

            # Case: only last name. Add a penalty of 3 for missing first name
            # Ex: smith
            score4 = self.match_last_name(lname, email_pre)
            if score4: score4 = (score4[0] + 3, f'Only last name|{score4[1]}')

            # Case: first name and last name concatenated
            # Ex: johnsmith
            lname_len = len(lname)
            part1 = email_pre[:-lname_len]
            part2 = email_pre[-lname_len:]
            score5 = self.match_name_parts_one_way(fname, lname, part1, part2)
            if score5: score5 = (score5[0], f'First-name then last-name|{score5[1]}')

            # Case: last name and first name concatenated:
            # Ex: smithjohn
            lname_len = len(lname)
            part1 = email_pre[lname_len:]
            part2 = email_pre[:lname_len]
            score6 = self.match_name_parts_one_way(fname, lname, part1, part2)
            if score6: score6 = (score6[0], f'Last-name then first-name|{score6[1]}')

            scores = [score1, score2, score3, score4, score5, score6, score7, score8]
            scores = [score for score in scores if score is not None]
            if len(scores):
                argmin = np.argmin([a[0] for a in scores])
                return scores[argmin][0], f'Name parts not separated|{scores[argmin][1]}'
        
        return None

    def match_name_parts_one_way(self, first_name, last_name, first_name_cand, last_name_cand):
        '''
        Try to match first_name and last_name with (part1, part2)
        
        Parameters
        ----------
        first_name: first name
        last_name: last name
        first_name_cand: candidate to compare with first name
        last_name_cand: candidate to compare with last name
        '''
        if first_name_cand == '' or last_name_cand == '':
            return None

        score_first_name = self.match_first_name(first_name, first_name_cand)
        score_last_name = self.match_last_name(last_name, last_name_cand)

        # Both first-name and last-name match
        if score_first_name and score_last_name:
            return score_first_name[0] + score_last_name[0], score_first_name[1] + ' && ' + score_last_name[1]

        # Only first-name match, Add a penalty of 8 because last-name doesn't match
        if score_first_name:
            return 8 + score_first_name[0], 'Only first-name match|' + score_first_name[1]

        # Only last-name match, Add a penalty of 8 because first-name doesn't match
        if score_last_name:
            return 8 + score_last_name[0], 'Only last-name match|' + score_last_name[1]

        return None

    def preprocess_email(self, email):
        '''
        Keeps only part before the @, and remove digits from the email
        
        Parameters
        ----------
        email: email to be preprocessed
        '''
        # Convert to lowercase
        email_pre = email.lower()
        
        # Keep only email prefix
        email_pre = email_pre.split('@')[0]
        
        # Remove any digit from email prefix
        email_pre = ''.join(filter(lambda x: not x.isdigit(), email_pre))
        return email_pre
        
    def match_name_parts(self, first_name, last_name, part1, part2):
        '''
        Try to match first name and last name with (part1, part2) or (part2, part1), 
        and take minimal score if found
        
        Parameters
        ----------
        first_name: first name
        last_name: last name
        part1: first part of the prefix, to compare with either first or last name
        part2: second part of the prefix, to compare with either first or last name
        '''
        if part1 == '' or part2 == '':
            return None

        # Try both ways
        score1 = self.match_name_parts_one_way(first_name, last_name, part1, part2)
        score2 = self.match_name_parts_one_way(first_name, last_name, part2, part1)

        scores = [score for score in [score1, score2] if score is not None]
        if len(scores):
            argmin = np.argmin([a[0] for a in scores])
            return scores[argmin]
    
    def match_first_name(self, first_name, cand):
        '''
        Returns a penalty on how far cand and first_name match, or None if they don't match
        Add any combination with nicknames
        
        Parameters
        ----------
        first_name: first name
        cand: candidate to compare with first name
        '''
        if cand == '':
            return None

        # If cand and first_name match, return 0
        if cand == first_name:
            return 0, 'Same first-name'

        # If cand and first_name match with one of their nicknames, return 1
        cand_nicknames = list(set(self.name2nick.get(cand, []) + [cand]))
        first_name_nicknames = list(set(self.name2nick.get(first_name, []) + [first_name]))
        if any([cand_nick in first_name_nicknames for cand_nick in cand_nicknames]):
            return 1, 'Same nickname'

        # If cand and first_name match their first characters, return 1
        if first_name[:len(cand)] == cand:
            return 1, 'Same first-name first chars'

        # If cand and first_name first and any of their nicknames match their first character, return 3
        if any([name_nick[:len(cand)] == cand for name_nick in first_name_nicknames]):
            return 3, 'Same nickname first chars'

        return None
    
    def match_last_name(self, last_name, cand):
        '''
        Returns a penalty on how far cand and last_name match, or None if they don't match
        
        Parameters
        ----------
        last_name: last name
        cand: candidate to compare with last name
        '''
        if cand == '':
            return None

        # If exacts same name, return 0
        if last_name == cand:
            return 0, 'Same last-name'
        # If the first letters are the same, return 2
        if last_name[:len(cand)] == cand:
            return 2, 'Same last-name first chars'
        return None
    
    def parse_nickname_file(self, file_path):
        '''
        Parse nickname file into a dictionnary
        
        Parameters
        ----------
        file_path: path to the nickname config file
        '''
        # Initialize empty dicts, with default value as empty set
        name2nick = collections.defaultdict(set)
        see_alsos = collections.defaultdict(set)
        
        with open(file_path, errors='ignore', encoding='Latin-1') as file:
            for line in file:
                if line != os.linesep:
                    line_formatted = line.strip().lower().replace(';', '').replace('.', '').replace(os.linesep, '')
                    sees = next(iter(re.findall(r'\(see ([a-zA-Z, ]*)\)', line_formatted)), None)

                    line_formatted = re.sub(r'\(see [a-zA-Z, ]*\)', '', line_formatted)
                    line_formatted = line_formatted.split(' – ')[0]
                    cut = line_formatted.split(' \x96 ')
                    names = cut[0].split(', ')
                    names = [name.strip() for name in names]
                    if len(cut) == 2:
                        surnames = cut[1].split(', ')
                        surnames = set([name.strip() for name in surnames])
                    name2nick.update({name: surnames for name in names})

                    if sees:
                        sees = sees.split(', ')
                        sees = set([name.strip() for name in sees])
                        for see in sees:
                            for name in names:
                                see_alsos[name].update({see})

        for see, alsos in see_alsos.items():
            for also in alsos:
                name2nick[see].update(name2nick[also])

        name2nick = {key: list(set(list(val) + [key])) for key, val in name2nick.items()}
        more_name2nick = {}
        for key in name2nick:
            for nick in name2nick[key]:
                more_name2nick[nick] = name2nick[key]
        name2nick = more_name2nick

        return name2nick
      
result = pd.DataFrame(columns=["score","details"])
score = []
details = []
mails = kargs["mails"]
path = ".\\\\Temp"
nicks_file = os.path.getsize(path + "\\\\" + "nicknames")
mtch = matcher(nicks_file)
for mail in mails:
   email = list(mail.values())[0]
   scores = [mtch.match_email_name(email, row["firstname"], row["lastname"]) for _, row in df.iterrows()]
   score = scores[0][0]
   details = scores[0][1]
