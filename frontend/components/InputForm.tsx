import React, { useState } from "react";
import { Play } from "lucide-react";

interface InputFormProps {
  onSubmit: (data: any) => void;
  disabled: boolean;
}

const InputForm: React.FC<InputFormProps> = ({ onSubmit, disabled }) => {
  const [form, setForm] = useState({
    repo_url: "",
    team_name: "",
    leader_name: "",
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(form);
  };

  return (
    <div className="bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-xl">
      <h2 className="text-xl font-semibold mb-4 text-white">Project Details</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm text-slate-400 mb-1">
            GitHub Repository URL
          </label>
          <input
            required
            name="repo_url"
            value={form.repo_url}
            onChange={handleChange}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="https://github.com/user/repo"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Team Name
            </label>
            <input
              required
              name="team_name"
              value={form.team_name}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white"
              placeholder="Team Alpha"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Leader Name
            </label>
            <input
              required
              name="leader_name"
              value={form.leader_name}
              onChange={handleChange}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-white"
              placeholder="Alice"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={disabled}
          className={`w-full flex items-center justify-center gap-2 p-3 rounded-lg font-bold transition-all ${disabled ? "bg-slate-600 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-500 shadow-lg shadow-blue-500/20"}`}
        >
          {disabled ? (
            "Processing..."
          ) : (
            <>
              <Play size={18} /> RUN AGENT
            </>
          )}
        </button>
      </form>
    </div>
  );
};

export default InputForm;
