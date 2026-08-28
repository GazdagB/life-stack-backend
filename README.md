# LifeOS

A personal operating system for tracking and analyzing all aspects of my life.

## Planned Features

- Expense tracking
- Income tracking
- Goal management
- Habit tracking
- Workout tracking
- Notes and journaling
- Life analytics

## Tech Stack

- React
- FastAPI
- PostgreSQL

## Movie search

Movie search uses the OMDb API from the backend. Add `OMDB_API_KEY` to `.env` after
requesting a key at https://www.omdbapi.com/apikey.aspx. External ratings are shown
when OMDb provides them; IMDb, Rotten Tomatoes, and Metacritic coverage varies by title.

AI movie recommendations use the OpenAI Responses API. Add `OPENAI_API_KEY` to
`.env`; `OPENAI_MOVIE_MODEL` is optional and defaults to `gpt-5.6-luna`. Only the
10 most recently rated movie titles, basic metadata, personal scores, critiques,
and up to 250 saved-title exclusions are sent. Account identity is never included,
and API responses are requested with storage disabled.
