"""Lesson types for language classes.

Each type adds teaching rules for the student's AI (over MCP in get_lesson and in the
copy-paste prompt). "general" keeps the plain lesson behaviour.
"""

GENERAL = "general"

KINDS: dict[str, dict] = {
    GENERAL: {
        "label": "General lesson",
        "rules": "",
    },
    "grammar": {
        "label": "Grammar",
        "rules": (
            "GRAMMAR LESSON. 1) Show the rule simply (form + when to use it), with a short Persian explanation if "
            "my level is low. 2) Give 3-4 clear examples, then contrast with a common Persian-speaker mistake. "
            "3) Controlled practice: 6-8 short exercises one at a time (fill the gap, choose the form, fix the "
            "mistake, transform the sentence). Wait for my answer, correct it and say why. 4) Free practice: ask me "
            "to write 2-3 sentences of my own with the structure and correct them. Track which forms I get wrong "
            "and list them as difficult concepts."
        ),
    },
    "vocabulary": {
        "label": "Vocabulary",
        "rules": (
            "VOCABULARY LESSON. Teach the words in small sets of 5-7. For each word give: the meaning in Persian, "
            "part of speech, a simple pronunciation hint, one natural example sentence and a common collocation. "
            "After each set, check recall: ask me the English word for the Persian meaning, or to complete a "
            "sentence, mixing older words back in. At the end do a quick recall round of all words. Put the words "
            "I did not remember in the difficult concepts."
        ),
    },
    "translation": {
        "label": "Persian → English translation + grammar",
        "rules": (
            "TRANSLATION LESSON (Persian to English). Give me ONE Persian sentence at a time, at my level, built "
            "around the lesson's grammar and words; start easy and get harder. I translate it into English. Then: "
            "say whether it is correct, show a natural correct translation, and explain each mistake with the grammar "
            "point behind it (tense, word order, articles, prepositions…) in one or two lines. Never give the "
            "translation before I try. Do 8-10 sentences. Keep a count of correct translations and list the grammar "
            "points I got wrong as difficult concepts; mention the count in the summary."
        ),
    },
    "speaking": {
        "label": "Speaking",
        "rules": (
            "SPEAKING LESSON. Ask me to answer by voice (the microphone button in the app); typing is fine if I "
            "can't. Give me a topic or question at my level, one at a time, with 2-3 useful phrases I can use. After "
            "each answer give short feedback: one thing I did well, up to two corrections (grammar or word choice) "
            "and a better model answer. Encourage longer answers step by step. Note fluency problems and repeated "
            "errors as difficult concepts."
        ),
    },
    "conversation": {
        "label": "Conversation / role-play",
        "rules": (
            "ROLE-PLAY LESSON. Set a real-life scene from the lesson (for example ordering food, a job interview, "
            "asking for directions). Tell me my role and the goal in one line, give 3-4 useful phrases, then play "
            "the other person and stay in character. Keep your turns short so I talk more. Do not interrupt for "
            "small mistakes: after the role-play, list my main mistakes with corrections and replay the hardest "
            "part once. Note what blocked me as difficult concepts."
        ),
    },
    "reading": {
        "label": "Reading",
        "rules": (
            "READING LESSON. Give me a short text at my level (or the lesson text). Before reading, pre-teach 3-5 "
            "key words. Then ask comprehension questions one at a time: main idea, details, then one inference "
            "question. After that, pick 3-5 useful words or phrases from the text and check them. Note the "
            "questions and words I got wrong as difficult concepts."
        ),
    },
    "writing": {
        "label": "Writing",
        "rules": (
            "WRITING LESSON. Give me a writing task at my level (a message, email, short paragraph or story) with "
            "a short model and useful phrases. I write it. Then give feedback: what works, the main errors grouped "
            "by type (grammar, vocabulary, punctuation, organisation) with corrections, and a corrected version. "
            "Ask me to rewrite one part using the feedback. Note the error types as difficult concepts."
        ),
    },
    "pronunciation": {
        "label": "Pronunciation",
        "rules": (
            "PRONUNCIATION LESSON. Ask me to answer by voice. Focus on the sounds in the lesson, especially ones "
            "that are hard for Persian speakers (th, w/v, short vs long vowels, consonant clusters, word stress). "
            "Explain how to make the sound, give minimal pairs and short sentences to repeat, and tell me which "
            "words sounded wrong (if your app cannot hear audio, use the transcript and spelling). Note the hard "
            "sounds as difficult concepts."
        ),
    },
}

CHOICES = [(key, value["label"]) for key, value in KINDS.items()]


def rules(kind: str) -> str:
    return KINDS.get(kind or GENERAL, KINDS[GENERAL])["rules"]
