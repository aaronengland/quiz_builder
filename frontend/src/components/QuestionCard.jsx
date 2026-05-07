const OPTIONS = ['A', 'B', 'C', 'D']

export default function QuestionCard({ question, index, selectedAnswer, onSelect }) {
  return (
    <div className="question-card">
      <h3 className="question-number">Question {index + 1}</h3>
      <p className="question-text">{question.question_text}</p>

      <div className="options">
        {OPTIONS.map((letter) => {
          const optionKey = `option_${letter.toLowerCase()}`
          const isSelected = selectedAnswer === letter

          return (
            <label
              key={letter}
              className={`option ${isSelected ? 'selected' : ''}`}
            >
              <input
                type="radio"
                name={`question-${question.id}`}
                value={letter}
                checked={isSelected}
                onChange={() => onSelect(letter)}
              />
              <span className="option-letter">{letter}</span>
              <span className="option-text">{question[optionKey]}</span>
            </label>
          )
        })}
      </div>
    </div>
  )
}
