import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

export default function History() {
  const [quizzes, setQuizzes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/quizzes')
      .then((resp) => {
        if (!resp.ok) throw new Error('Failed to load history')
        return resp.json()
      })
      .then(setQuizzes)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading-state"><div className="spinner" /></div>
  if (error) return <p className="error-message">{error}</p>

  return (
    <div className="history-page">
      <h2>Quiz History</h2>

      {quizzes.length === 0 ? (
        <div className="empty-state">
          <p>No quizzes yet. Generate your first quiz!</p>
          <Link to="/" className="btn btn-primary">Create Quiz</Link>
        </div>
      ) : (
        <div className="history-list">
          {quizzes.map((quiz) => (
            <div key={quiz.id} className="history-card">
              <div className="history-info">
                <h3>{quiz.topic}</h3>
                <p className="history-date">
                  {new Date(quiz.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
                {quiz.latest_score !== null && (
                  <p className="history-score">
                    Score: {quiz.latest_score}/{quiz.total}
                  </p>
                )}
              </div>
              <div className="history-actions">
                <Link to={`/quiz/${quiz.id}`} className="btn btn-sm btn-secondary">
                  Retake
                </Link>
                {quiz.latest_score !== null && (
                  <Link to={`/results/${quiz.id}`} className="btn btn-sm btn-primary">
                    Results
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
