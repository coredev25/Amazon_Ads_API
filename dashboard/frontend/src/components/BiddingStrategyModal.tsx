'use client';

import React, { useState, useEffect } from 'react';
import { X, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';
import { fetchBiddingStrategies, previewBiddingStrategy, executeBiddingStrategy, type BiddingStrategy } from '@/utils/api';
import { formatCurrency, formatPercentage } from '@/utils/helpers';

interface BiddingStrategyModalProps {
  isOpen: boolean;
  onClose: () => void;
  keywordIds: number[];
  onExecute?: (result: any) => void;
}

export default function BiddingStrategyModal({
  isOpen,
  onClose,
  keywordIds,
  onExecute,
}: BiddingStrategyModalProps) {
  const [strategies, setStrategies] = useState<BiddingStrategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<BiddingStrategy | null>(null);
  const [parameters, setParameters] = useState<Record<string, any>>({});
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'select' | 'configure' | 'preview' | 'executing'>('select');

  useEffect(() => {
    if (isOpen) {
      loadStrategies();
    }
  }, [isOpen]);

  const loadStrategies = async () => {
    try {
      const data = await fetchBiddingStrategies();
      setStrategies(data);
    } catch (err) {
      setError('Failed to load bidding strategies');
      console.error(err);
    }
  };

  const handleSelectStrategy = (strategy: BiddingStrategy) => {
    setSelectedStrategy(strategy);
    // Initialize parameters with defaults
    const initParams: Record<string, any> = {};
    strategy.parameters.forEach(param => {
      initParams[param.name] = param.default;
    });
    setParameters(initParams);
    setStep('configure');
  };

  const handleParameterChange = (paramName: string, value: any) => {
    setParameters(prev => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const handlePreview = async () => {
    if (!selectedStrategy) return;
    
    setLoading(true);
    setError('');
    try {
      const data = await previewBiddingStrategy(selectedStrategy.id, keywordIds, parameters);
      setPreview(data);
      setStep('preview');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate preview');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!selectedStrategy || !preview) return;
    
    setExecuting(true);
    setError('');
    try {
      const result = await executeBiddingStrategy(selectedStrategy.id, keywordIds, parameters);
      setStep('executing');
      
      // Show success for 2 seconds
      setTimeout(() => {
        onExecute?.(result);
        handleClose();
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to execute strategy');
      setExecuting(false);
    }
  };

  const handleClose = () => {
    setSelectedStrategy(null);
    setParameters({});
    setPreview(null);
    setError('');
    setStep('select');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-6 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {step === 'executing' ? 'Applying Strategy' : 'Bidding Strategies'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {step === 'select' && `Select a strategy for ${keywordIds.length} keyword(s)`}
              {step === 'configure' && `Configure ${selectedStrategy?.name}`}
              {step === 'preview' && 'Review projected changes'}
              {step === 'executing' && 'Committing changes...'}
            </p>
          </div>
          {step !== 'executing' && (
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="w-6 h-6" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-900 dark:text-red-200">{error}</p>
              </div>
            </div>
          )}

          {/* Step 1: Select Strategy */}
          {step === 'select' && (
            <div className="grid grid-cols-1 gap-3">
              {strategies.map(strategy => (
                <button
                  key={strategy.id}
                  onClick={() => handleSelectStrategy(strategy)}
                  className="text-left p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-amazon-orange hover:bg-orange-50 dark:hover:bg-orange-900/10 transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white">{strategy.name}</h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{strategy.description}</p>
                    </div>
                    <span className={`badge ${
                      strategy.category === 'defensive' ? 'badge-warning' :
                      strategy.category === 'balanced' ? 'badge-info' :
                      'badge-secondary'
                    }`}>
                      {strategy.category}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    <strong>Expected Impact:</strong> {strategy.expected_impact}
                  </p>
                </button>
              ))}
            </div>
          )}

          {/* Step 2: Configure Parameters */}
          {step === 'configure' && selectedStrategy && (
            <div className="space-y-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">{selectedStrategy.name}</h3>
                <p className="text-sm text-blue-800 dark:text-blue-300">{selectedStrategy.description}</p>
              </div>

              {selectedStrategy.parameters.map(param => (
                <div key={param.name}>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {param.label}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type={param.type === 'number' ? 'number' : 'text'}
                      value={parameters[param.name]}
                      onChange={(e) => handleParameterChange(param.name, 
                        param.type === 'number' ? parseFloat(e.target.value) : e.target.value
                      )}
                      min={param.min}
                      max={param.max}
                      step={param.step || 1}
                      className="input flex-1"
                    />
                    {param.name.includes('percentage') && <span className="text-gray-600 dark:text-gray-400">%</span>}
                    {param.name.includes('multiplier') && <span className="text-gray-600 dark:text-gray-400">x</span>}
                  </div>
                  {param.description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{param.description}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Step 3: Preview */}
          {step === 'preview' && preview && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Keywords</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{preview.total_keywords}</p>
                </div>
                <div className={`rounded-lg p-3 ${
                  preview.total_spend_change > 0 ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'
                }`}>
                  <p className={`text-xs ${
                    preview.total_spend_change > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                  }`}>
                    Spend Change
                  </p>
                  <p className={`text-2xl font-bold ${
                    preview.total_spend_change > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'
                  }`}>
                    {formatCurrency(preview.total_spend_change)}
                  </p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Change %</p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {preview.spend_change_percentage > 0 ? '+' : ''}{preview.spend_change_percentage.toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* Changes Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 dark:bg-gray-800">
                    <tr>
                      <th className="text-left px-3 py-2 font-semibold text-gray-900 dark:text-white">Keyword</th>
                      <th className="text-right px-3 py-2 font-semibold text-gray-900 dark:text-white">Current</th>
                      <th className="text-right px-3 py-2 font-semibold text-gray-900 dark:text-white">New</th>
                      <th className="text-right px-3 py-2 font-semibold text-gray-900 dark:text-white">Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {preview.projected_changes.slice(0, 10).map((change: any, idx: number) => (
                      <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                        <td className="px-3 py-2 text-gray-900 dark:text-white">{change.keyword}</td>
                        <td className="text-right px-3 py-2 text-gray-600 dark:text-gray-400">
                          {formatCurrency(change.current_bid)}
                        </td>
                        <td className="text-right px-3 py-2 text-gray-900 dark:text-white font-medium">
                          {formatCurrency(change.new_bid)}
                        </td>
                        <td className={`text-right px-3 py-2 font-medium flex items-center justify-end gap-1`}>
                          {change.change_percentage > 0 ? (
                            <TrendingUp className="w-4 h-4 text-red-600 dark:text-red-400" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-green-600 dark:text-green-400" />
                          )}
                          <span className={change.change_percentage > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}>
                            {change.change_percentage > 0 ? '+' : ''}{change.change_percentage.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {preview.projected_changes.length > 10 && (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  ... and {preview.projected_changes.length - 10} more keywords
                </p>
              )}
            </div>
          )}

          {/* Step 4: Executing */}
          {step === 'executing' && (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 dark:bg-green-900/20 rounded-full mb-4">
                <svg className="w-6 h-6 text-green-600 dark:text-green-400 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <p className="text-lg font-medium text-gray-900 dark:text-white">Applying strategy...</p>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">Please wait while bid changes are committed</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-6 flex items-center justify-between">
          <button
            onClick={handleClose}
            className="btn btn-secondary"
            disabled={executing}
          >
            {step === 'preview' ? 'Back' : 'Cancel'}
          </button>
          
          {step === 'select' && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Select a strategy to continue
            </p>
          )}
          
          {step === 'configure' && (
            <button
              onClick={handlePreview}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Generating Preview...' : 'Preview Changes'}
            </button>
          )}
          
          {step === 'preview' && (
            <button
              onClick={handleExecute}
              disabled={executing}
              className="btn btn-primary bg-green-600 hover:bg-green-700"
            >
              {executing ? 'Applying...' : 'Apply Strategy'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
