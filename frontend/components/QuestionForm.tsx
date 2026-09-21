import { FormEvent, useState } from 'react';
import { troubleshoot, TroubleshootResponse } from '../src/api';

interface QuestionFormProps {
  onResult: (result: TroubleshootResponse) => void;
}

export default function QuestionForm({ onResult }: QuestionFormProps) {
  const [equipment, setEquipment] = useState('Centrifugal pump');
  const [problem, setProblem] = useState('Discharge pressure is low.');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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

  return <form onSubmit={submit}>
    <label>Equipment<input value={equipment} onChange={(event) => setEquipment(event.target.value)} /></label>
    <label>Problem<textarea value={problem} onChange={(event) => setProblem(event.target.value)} /></label>
    <button type="submit" disabled={loading}>{loading ? 'Analyzing...' : 'Ask PlantOps AI'}</button>
    {error && <p role="alert">{error}</p>}
  </form>;
}
