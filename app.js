import { arabicWords } from './words.js';

class QuranWordMemorizationApp {
  constructor() {
    this.words = arabicWords;
    this.currentWord = null;
    this.memorizedWords = new Map(); // word -> stage
    this.difficultWords = new Map();
    this.recentlyLearned = [];
    
    // Get the maximum stage number from the words data
    this.totalStages = Math.max(...this.words.map(word => word.stage));
    
    this.lastAction = null;
    
    this.initializeElements();
    this.setupEventListeners();
    this.populateStageSelect();
    this.loadRandomWord();
  }

  initializeElements() {
    this.arabicWordElement = document.getElementById('arabicWord');
    this.transliterationElement = document.getElementById('transliteration');
    this.translationElement = document.getElementById('translation');
    this.partOfSpeechElement = document.getElementById('partOfSpeech');
    this.frequencyElement = document.getElementById('frequency');
    this.stageLevelElement = document.getElementById('stageLevel');
    
    this.totalWordsElement = document.getElementById('totalWords');
    this.memorizedWordsElement = document.getElementById('memorizedWords');
    this.progressElement = document.getElementById('progress');
    this.currentStageElement = document.getElementById('currentStage');
    
    this.undoActionBtn = document.getElementById('undoAction');
    this.knowWordBtn = document.getElementById('knowWord');
    this.dontKnowWordBtn = document.getElementById('dontKnowWord');
    
    this.frequencyFilterInput = document.getElementById('frequencyFilter');
    this.frequencyValueElement = document.getElementById('frequencyValue');
    this.repetitionModeSelect = document.getElementById('repetitionMode');
    this.stageSelectElement = document.getElementById('stageSelect');
    
    this.difficultWordsListElement = document.getElementById('difficultWordsList');
    this.recentlyLearnedWordsElement = document.getElementById('recentlyLearnedWords');
  }

  populateStageSelect() {
    // Clear existing options first
    this.stageSelectElement.innerHTML = '';
    
    // Add default 'All Stages' option
    const allStagesOption = document.createElement('option');
    allStagesOption.value = 'all';
    allStagesOption.textContent = 'All Stages';
    this.stageSelectElement.appendChild(allStagesOption);

    // Add individual stage options
    for (let i = 1; i <= this.totalStages; i++) {
      const option = document.createElement('option');
      option.value = i;
      option.textContent = `Stage ${i}`;
      this.stageSelectElement.appendChild(option);
    }

    this.stageSelectElement.addEventListener('change', () => {
      const selectedStage = this.stageSelectElement.value;
      this.loadWordsByStage(selectedStage);
    });
  }

  setupEventListeners() {
    this.undoActionBtn.addEventListener('click', () => this.undoLastAction());
    this.knowWordBtn.addEventListener('click', () => this.markWordAsKnown());
    this.dontKnowWordBtn.addEventListener('click', () => this.markWordAsDifficult());
    
    this.frequencyFilterInput.addEventListener('input', (e) => {
      this.frequencyValueElement.textContent = e.target.value;
      this.loadRandomWord();
    });
    
    this.repetitionModeSelect.addEventListener('change', () => this.loadRandomWord());
  }

  loadRandomWord() {
    const currentStage = this.stageSelectElement.value;
    if (currentStage === 'all') {
      return this.loadWordsByStage('all');
    }

    const stageNum = parseInt(currentStage, 10);
    // Filter by both frequency and exact stage match
    const filteredWords = this.words.filter(word => 
      word.stage === stageNum &&
      word.frequency > parseInt(this.frequencyFilterInput.value)
    );
    
    const mode = this.repetitionModeSelect.value;
    if (mode === 'weakest') {
      this.currentWord = this.getWeakestWord(filteredWords);
    } else {
      this.currentWord = this.getRandomWord(filteredWords);
    }
    
    this.updateWordDisplay();
  }

  loadWordsByStage(stage) {
    let filteredWords;
    
    if (stage === 'all') {
      filteredWords = this.words;
    } else {
      const stageNum = parseInt(stage, 10);
      // Filter words that exactly match the selected stage
      filteredWords = this.words.filter(word => word.stage === stageNum);
    }

    if (filteredWords.length > 0) {
      this.currentWord = this.getRandomWord(filteredWords);
      this.updateWordDisplay();
      this.updateStats();
    } else {
      alert(`No words found for Stage ${stage}`);
    }
  }

  getRandomWord(wordList) {
    return wordList[Math.floor(Math.random() * wordList.length)];
  }

  getWeakestWord(wordList) {
    const currentStage = parseInt(this.stageSelectElement.value) || 1;
    // Only get words from the exact stage
    const eligibleWords = wordList.filter(word => 
      word.stage === currentStage && 
      (!this.memorizedWords.has(word) || this.memorizedWords.get(word) < this.totalStages)
    );
    
    return eligibleWords.length > 0 
      ? this.getRandomWord(eligibleWords)
      : this.getRandomWord(wordList);
  }

  updateWordDisplay() {
    const currentStage = this.stageSelectElement.value;
    if (!currentStage || !this.currentWord) return;

    this.arabicWordElement.textContent = this.currentWord.word;
    this.transliterationElement.textContent = this.currentWord.transliteration || 'N/A';
    this.translationElement.textContent = this.currentWord.translation;
    this.partOfSpeechElement.textContent = `Part of Speech: ${this.currentWord.partOfSpeech}`;
    this.frequencyElement.textContent = `Frequency: ${this.currentWord.frequency}`;
    
    const memorizedStage = this.memorizedWords.get(this.currentWord) || 1;
    this.stageLevelElement.textContent = `Stage ${currentStage} - Progress: ${memorizedStage}/${this.totalStages}`;
    
    this.updateStats();
  }

  markWordAsKnown() {
    // Store the last action for potential undo
    this.lastAction = {
      type: 'known',
      word: this.currentWord,
      prevStage: this.memorizedWords.get(this.currentWord) || 1
    };

    const currentStage = this.memorizedWords.get(this.currentWord) || 1;
    const nextStage = Math.min(currentStage + 1, this.totalStages);
    
    this.memorizedWords.set(this.currentWord, nextStage);
    this.recentlyLearned.unshift({...this.currentWord, stage: nextStage});
    this.recentlyLearned = this.recentlyLearned.slice(0, 5);
    
    this.loadRandomWord();
    this.updateRecentlyLearnedDisplay();
    this.updateStats();
  }

  markWordAsDifficult() {
    // Store the last action for potential undo
    this.lastAction = {
      type: 'difficult',
      word: this.currentWord,
      prevStage: this.memorizedWords.get(this.currentWord) || 1
    };

    const currentStage = this.memorizedWords.get(this.currentWord) || 1;
    const newStage = Math.max(1, currentStage - 1);
    
    this.memorizedWords.set(this.currentWord, newStage);
    
    const difficulty = this.difficultWords.get(this.currentWord) || 0;
    this.difficultWords.set(this.currentWord, difficulty + 1);
    
    this.loadRandomWord();
    this.updateDifficultWordsDisplay();
    this.updateStats();
  }

  undoLastAction() {
    if (!this.lastAction) return;

    // Revert the stage
    this.memorizedWords.set(this.lastAction.word, this.lastAction.prevStage);

    // Remove from difficult words or recently learned based on action type
    if (this.lastAction.type === 'difficult') {
      const currentDifficulty = this.difficultWords.get(this.lastAction.word) || 0;
      if (currentDifficulty > 1) {
        this.difficultWords.set(this.lastAction.word, currentDifficulty - 1);
      } else {
        this.difficultWords.delete(this.lastAction.word);
      }
      this.updateDifficultWordsDisplay();
    } else if (this.lastAction.type === 'known') {
      // Remove from recently learned if it was the first item
      if (this.recentlyLearned[0] && this.recentlyLearned[0].word === this.lastAction.word.word) {
        this.recentlyLearned.shift();
      }
      this.updateRecentlyLearnedDisplay();
    }

    // Show the last word again
    this.currentWord = this.lastAction.word;
    this.updateWordDisplay();

    // Clear the last action
    this.lastAction = null;
  }

  updateDifficultWordsDisplay() {
    const currentStage = this.stageSelectElement.value;
    if (currentStage === 'all') return;
    
    const stageNum = parseInt(currentStage, 10);
    const stageDifficultWords = [...this.difficultWords.entries()]
      .filter(([word]) => word.stage === stageNum)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    
    this.difficultWordsListElement.innerHTML = stageDifficultWords
      .map(([word, difficulty]) => `<li>${word.word} (${difficulty} times)</li>`)
      .join('');
  }

  updateRecentlyLearnedDisplay() {
    const currentStage = this.stageSelectElement.value;
    if (currentStage === 'all') return;
    
    const stageNum = parseInt(currentStage, 10);
    const stageRecentlyLearned = this.recentlyLearned
      .filter(word => word.stage === stageNum)
      .slice(0, 5);
    
    this.recentlyLearnedWordsElement.innerHTML = stageRecentlyLearned
      .map(word => `<li>${word.word} (Progress: ${this.memorizedWords.get(word) || 1}/${this.totalStages})</li>`)
      .join('');
  }

  updateStats() {
    const currentStage = this.stageSelectElement.value;
    
    if (currentStage === 'all') {
      // Stats for all words
      this.totalWordsElement.textContent = `Total Words: ${this.words.length}`;
      const totalMemorized = this.words.filter(word => 
        this.memorizedWords.has(word) && 
        this.memorizedWords.get(word) === this.totalStages
      ).length;
      this.memorizedWordsElement.textContent = `Memorized: ${totalMemorized}/${this.words.length}`;
      const totalProgress = Math.round((totalMemorized / this.words.length) * 100);
      this.progressElement.textContent = `Progress: ${totalProgress}%`;
      this.currentStageElement.textContent = `Stage: All`;
    } else {
      // Stats for current stage only
      const stageNum = parseInt(currentStage, 10);
      const stageWords = this.words.filter(word => word.stage === stageNum);
      
      this.totalWordsElement.textContent = `Stage ${stageNum} Words: ${stageWords.length}`;
      const memorizedInStage = stageWords.filter(word => 
        this.memorizedWords.has(word) && 
        this.memorizedWords.get(word) === this.totalStages
      ).length;
      this.memorizedWordsElement.textContent = 
        `Stage ${stageNum} Memorized: ${memorizedInStage}/${stageWords.length}`;
      
      const progress = stageWords.length > 0 
        ? Math.round((memorizedInStage / stageWords.length) * 100)
        : 0;
      this.progressElement.textContent = `Stage ${stageNum} Progress: ${progress}%`;
      this.currentStageElement.textContent = `Current Stage: ${stageNum}`;
    }
  }
}

const app = new QuranWordMemorizationApp();