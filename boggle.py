#sowpods from https://www.wordgamedictionary.com/sowpods/download/sowpods.txt
#compare to https://www.toptal.com/java/the-trie-a-neglected-data-structure

import numpy as np
import pandas as pd
import random
from collections import defaultdict
from datetime import datetime
import dill as pkl
import os
import urllib.parse

data_dir = 'https://raw.githubusercontent.com/bernardbeckerman/boggle/master/data/'
ISSUE_BASE_URL = 'https://github.com/bernardbeckerman/bernardbeckerman/issues/new?title=shake&body='

#make trie of all English words
def make_trie(mydict='sowpods'):
    trie_head = {'children':{}, 'is_word':False}
    if mydict is not 'sowpods':
        raise ValueError('Not programmed for dictionary ' + mydict + '.')
    mydict = pd.read_csv(data_dir + mydict + '.txt'
                         , keep_default_na=False
                         , na_values=['']
                         , header = None)
    for nline,line in mydict.iloc[:, 0].items():
        if (' ' in line) or (len(line) == 0):
            continue
        word = line.strip()
        curr_node = trie_head
        for ichar in word:
            if ichar not in curr_node['children']:
                curr_node['children'][ichar] = {'children':{}, 'is_word':False}
            curr_node = curr_node['children'][ichar]
        curr_node['is_word'] = True
    #insert pickle here
    return trie_head

#check if word is in trie
def check_word(word, trie_head):
    curr_node = trie_head
    for ichar in word:
        if ichar not in curr_node['children']:
            return False
        curr_node = curr_node['children'][ichar]
    return curr_node['is_word']

# sum the scores of a list of words
def sum_word_scores(words, scoring = "standard"):
    words = set(words)
    if scoring is not 'standard':
        raise ValueError('Not currently programmed for non-standard scoring.')
    scoring_dict = {0:0,1:0,2:0,3:1,4:1,5:2,6:3,7:5}
    scoring_dict = defaultdict(lambda:11, scoring_dict)
    score = 0
    for word in words:
        score += scoring_dict[len(word)]
    return score

def get_trie_size(my_trie):
    trie_sum = 1
    for letter,child in my_trie['children'].items():
        trie_sum += get_trie_size(child)
    return(trie_sum)

#class managing dice
class Die:
    #create die with given sides
    def __init__(self, sides):
        if len(sides) != 6:
            raise ValueError('Die {} should have six sides.'.format(sides))
        self.sides = sides
    #roll the die
    def roll(self):
        return random.choice(self.sides)
    
#class managing board
class Board:

    #initialize NxM boggle board - defaults to 4x4
    def __init__(self, dice='standard', n=4, m=4, qu_pip = True):
        if dice is not 'standard':
            raise ValueError('Not currently programmed for nonstandard dice.')
        self.trie_head = make_trie()
        self.dice = [Die([ichar for ichar in die.strip()]) for num,die in pd.read_csv(data_dir + dice + '_dice.txt', header = None).iloc[:, 0].items()]
        self.n = n
        self.m = m
        if len(self.dice) != n*m:
            raise ValueError('Number of dice {} not equal to {}x{}. Please add dice or change grid dimensions.'.format(len(dice),n,m))
        self.qu_pip = qu_pip

    #shake board
    def shake(self):
        random.shuffle(self.dice)
        self.grid = []
        for die in self.dice:
            self.grid.append(die.roll())
        self.grid = np.reshape(self.grid,[self.n,self.m])

    #recursive fn that checks if pattern 'word' is a word
    def find_words_from(self, i, j, curr_node, word, visited):
        #import pdb
        #pdb.set_trace()
        visited[i][j] = 1
        word.append(self.grid[i][j])
        child_node = curr_node['children'][self.grid[i][j]]
        if self.qu_pip and self.grid[i][j] == 'q':
            if 'u' not in child_node['children']:
                return
            word.append('u')
            child_node = child_node['children']['u']
        if child_node['is_word']:
            self.words.append(''.join(word))
        #keep dict of neighbors:locations
        for ineigh in range(max(0, i - 1), min(i + 2, self.n)):
            for jneigh in range(max(0, j - 1), min(j + 2, self.m)):
                if ineigh == i and jneigh == j:
                    continue
                ichar = self.grid[ineigh][jneigh]
                if (visited[ineigh][jneigh] == 0) and (ichar in child_node['children'].keys()):
                    self.find_words_from(ineigh, jneigh, child_node.copy(), word = word.copy(), visited = np.copy(visited))
                    
    #finds all words in current board arrangement using recursive fn above
    def find_words(self):
        self.words = []
        for i in range(self.n):
            for j in range(self.m):
                self.find_words_from(i, j, self.trie_head, [], np.zeros([self.n, self.m]))
        self.words = sorted(set(self.words))
        return self.words

    def play(self, play_minutes = 3):
        self.shake()
        user_words = []
        self.display()
        start_time = datetime.now()
        while True:
            word = input("Enter word:")
            if (datetime.now() - start_time).seconds > (play_minutes * 60):
                break
            user_words.append(word)
        print("game over! scoring...")
        user_words = set(user_words)
        valid_words = [word for word in user_words if check_word(word, self.trie_head) == True]
        invalid_words = [word for word in user_words if check_word(word, self.trie_head) == False]
        valid_words.sort()
        invalid_words.sort()
        all_words = sorted(set(self.find_words()))
        
        print()
        print("your valid words: " + ", ".join(valid_words))
        print()
        print("your invalid words: " + ", ".join(invalid_words))
        print()
        print("your score: " + str(sum_word_scores(set(valid_words))))
        print()
        print("all valid words: " + ", ".join(all_words))
        print()
        print("total possible: " + str(sum_word_scores(all_words)))

    def play_github(self, user_words = None, play_minutes = 3):

        marker_line = "Write a comma-separated list of words below, then hit submit to score.\nDelete this line and everything above before submitting."
        # read user words from issue text
        if user_words is None:# or marker_line not in user_words:
            user_words = ['']
        else:
            #user_words = user_words.split(marker_line)[1]
            user_words = [istr.strip().lower() for istr in user_words.split(',')]

        # read old board from pkl
        with open('board.pkl', 'rb') as f:
            self.grid = pkl.load(f)

        # score old board
        self.find_words()

        # score user
        user_words = set(user_words)
        valid_words = [word for word in user_words if check_word(word, self.trie_head) == True]
        invalid_words = [word for word in user_words if check_word(word, self.trie_head) == False]
        all_words = sorted(set(self.find_words()))
        words_in_puzzle = set(valid_words).intersection(all_words)

        valid_words.sort()
        invalid_words.sort()

        readme_str = '\n\n'.join(["## Last board:"
                                  , self.display_github()
                                  , "latest score: " + str(sum_word_scores(set(words_in_puzzle)))
                                  , "highest possible: " + str(sum_word_scores(set(all_words)))
                                  , "your valid words:\n\n" + ", ".join(sorted(set(words_in_puzzle)))
                                  , "your invalid words:\n\n" + ", ".join(sorted(set(invalid_words)))
                                  , "words not in puzzle:\n\n" + ", ".join(sorted(set(valid_words) - set(words_in_puzzle)))
                                  , "all valid words:\n\n" + ", ".join(sorted(set(all_words)))
        ])
        
        # create and save new board
        self.shake()
        query = self.display_issue() + "\n" + marker_line + "\n\n"
        linkstr = ISSUE_BASE_URL + urllib.parse.quote(query)
        readme_str = '\n\n'.join(["# Hi, I'm Bernie 👋"
                                  , "Welcome to my GitHub readme. Why not join me for a game of boggle 🔠?"
                                  , "## Current board"
                                  , self.display_github()
                                  , "Valid words consist of strings of letters connected vertically, horizontally, or diagonally, with each letter being used at most once per word."
                                  , "[Click here](" + linkstr + ") to jot down some words, submit your score, and shake the board!"
                                  , readme_str])
        
        with open('board.pkl', 'wb') as f:
            pkl.dump(self.grid, f)
        # create new readme
        with open('README.md', 'w') as f:
            f.write(readme_str)

        # push to master
        os.system('git config --global user.name "GitHub Action Bot"')
        os.system('git config --global user.email "github-action-bot@example.com"')
        os.system('git add README.md board.pkl')
        os.system("git commit -m 'ROBOT: refreshing readme and board'")
        os.system('git push')
        
    def display(self):
        for irow in self.grid:
            line = ''
            for jletter in irow:
                line += jletter.upper() + ' '
            print(line)
        
    def display_github(self):
        grid_str = '```\n'
        for irow in self.grid:
            line = ''
            for jletter in irow:
                line += jletter.upper() + ' '
            grid_str += line + '\n'
        grid_str += '```'
        return(grid_str)

    def display_issue(self):
        grid_str = ''
        for irow in self.grid:
            line = ''
            for jletter in irow:
                line += jletter.upper() + ' '
                if jletter.upper() == "I":
                    line += ' '
            grid_str += line + '\n'
        return(grid_str)

def main(ngames):
    board = Board()
    counts = defaultdict(int)
    scores = []
    for i in range(ngames):
        board.shake()
        for word in board.find_words():
            counts[word] += 1
        scores.append(sum_word_scores(board.words))
    return scores, counts
if __name__ == '__main__': main()
