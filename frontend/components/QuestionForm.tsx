import { FormEvent, useState } from 'react';
import { troubleshoot, TroubleshootResponse } from '../src/api';

interface QuestionFormProps {
  onResult: (result: TroubleshootResponse) => void;
}

const equipmentOptions = ['Centrifugal pump', 'Heat exchanger', 'Compressor'];
const exampleQueries = {
  'Centrifugal pump': 'Discharge pressure is low.',
  'Heat exchanger': 'Outlet temperature is drifting high.',
  Compressor: 'High vibration alarm active during startup.',
};

export default function QuestionForm({ onResult }: QuestionFormProps) {
  const [equipment, setEquipment] = useState('Centrifugal pump');
  const [problem, setProblem] = useState(exampleQueries['Centrifugal pump']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleEquipmentChange(nextEquipment: string) {
    setEquipment(nextEquipment);
    const nextProblem = exampleQueries[nextEquipment as keyof typeof exampleQueries] ?? '';
    setProblem(nextProblem);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      onResult(await troubleshoot(equipment, problem));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to contact PlantOps AI.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <form className="ask-form" onSubmit={submit}>
      <div className="field-group">
        <label htmlFor="equipment">Equipment</label>
        <select id="equipment" value={equipment} onChange={(event) => handleEquipmentChange(event.target.value)}>
          {equipmentOptions.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>

      <div className="field-group">
        <label htmlFor="problem">Problem description</label>
        <textarea
          id="problem"
          rows={5}
          value={problem}
          onChange={(event) => setProblem(event.target.value)}
          placeholder="Describe the condition or alarm you are seeing..."
        />
      </div>

      <div className="form-actions">
        <button type="submit" disabled={loading}>
          {loading ? 'Analyzing operating data...' : 'Ask PlantOps AI'}
        </button>
      </div>

      {error && (
        <p className="error-banner" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
