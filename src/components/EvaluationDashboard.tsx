import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LineChart, Line, BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { AlertTriangle, CheckCircle, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface EvaluationDashboardProps {
  jobId?: string;
}

interface EvaluationResult {
  job_id: string;
  status: string;
  timestamp: string;
  aggregated_evaluation?: {
    aggregate_score: number;
    confidence: string;
    sources: string[];
    components: {
      [key: string]: {
        overall_score: number;
        scores: { [key: string]: number };
        explanations?: { [key: string]: { [key: string]: string } };
      };
    };
  };
  improvement_report?: {
    summary: string;
    strengths: Array<{ component: string; score: number; description: string }>;
    weaknesses: Array<{ component: string; score: number; description: string }>;
    priority_improvements: Array<{
      component: string;
      criterion: string;
      score: number;
      recommendation: string;
      details?: string;
    }>;
  };
}

export const EvaluationDashboard: React.FC<EvaluationDashboardProps> = ({ jobId }) => {
  const [evaluationData, setEvaluationData] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedComponent, setSelectedComponent] = useState<string>('summary');

  useEffect(() => {
    if (jobId) {
      fetchEvaluation();
    }
  }, [jobId]);

  const fetchEvaluation = async () => {
    if (!jobId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:8000/api/evaluation/${jobId}/status`);
      if (!response.ok) {
        throw new Error('Evaluation not found');
      }
      
      const data = await response.json();
      setEvaluationData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const triggerEvaluation = async () => {
    if (!jobId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`http://localhost:8000/api/evaluation/${jobId}/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          include_llm: true,
          include_metrics: true
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to trigger evaluation');
      }
      
      // Poll for results
      setTimeout(() => fetchEvaluation(), 2000);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number): string => {
    if (score >= 8) return 'text-green-600';
    if (score >= 6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getConfidenceBadgeColor = (confidence: string): string => {
    switch (confidence) {
      case 'high': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-4 w-4 animate-spin" />
            <span>Loading evaluation...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              {error}
              {jobId && (
                <Button 
                  onClick={triggerEvaluation} 
                  variant="outline" 
                  size="sm" 
                  className="ml-4"
                >
                  Trigger Evaluation
                </Button>
              )}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!evaluationData || !evaluationData.aggregated_evaluation) {
    return (
      <Card className="w-full">
        <CardContent className="p-6">
          <div className="text-center space-y-4">
            <p className="text-gray-500">No evaluation data available</p>
            {jobId && (
              <Button onClick={triggerEvaluation} variant="outline">
                Run Evaluation
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  const { aggregated_evaluation, improvement_report } = evaluationData;
  
  // Prepare data for charts
  const componentScores = Object.entries(aggregated_evaluation.components).map(([name, data]) => ({
    component: name,
    score: data.overall_score,
    ...data.scores
  }));

  const radarData = Object.entries(aggregated_evaluation.components).map(([name, data]) => ({
    component: name.charAt(0).toUpperCase() + name.slice(1),
    score: data.overall_score
  }));

  return (
    <div className="space-y-6">
      {/* Overall Summary */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Evaluation Overview</CardTitle>
              <CardDescription>
                Evaluated on {new Date(evaluationData.timestamp).toLocaleString()}
              </CardDescription>
            </div>
            <Button onClick={fetchEvaluation} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center">
              <div className={`text-3xl font-bold ${getScoreColor(aggregated_evaluation.aggregate_score)}`}>
                {aggregated_evaluation.aggregate_score.toFixed(1)}/10
              </div>
              <p className="text-sm text-gray-500">Overall Score</p>
            </div>
            <div className="text-center">
              <Badge className={getConfidenceBadgeColor(aggregated_evaluation.confidence)}>
                {aggregated_evaluation.confidence} confidence
              </Badge>
              <p className="text-sm text-gray-500 mt-2">Agreement Level</p>
            </div>
            <div className="text-center">
              <div className="flex justify-center gap-1">
                {aggregated_evaluation.sources.map((source) => (
                  <Badge key={source} variant="outline">{source}</Badge>
                ))}
              </div>
              <p className="text-sm text-gray-500 mt-2">Evaluation Sources</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Component Analysis */}
      <Card>
        <CardHeader>
          <CardTitle>Component Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs value={selectedComponent} onValueChange={setSelectedComponent}>
            <TabsList className="grid w-full grid-cols-4">
              {Object.keys(aggregated_evaluation.components).map((comp) => (
                <TabsTrigger key={comp} value={comp}>
                  {comp.charAt(0).toUpperCase() + comp.slice(1).replace('_', ' ')}
                </TabsTrigger>
              ))}
            </TabsList>
            
            {Object.entries(aggregated_evaluation.components).map(([comp, data]) => (
              <TabsContent key={comp} value={comp} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium mb-2">Scores by Criteria</h4>
                    {Object.entries(data.scores).map(([criterion, score]) => (
                      <div key={criterion} className="flex justify-between items-center py-2">
                        <span className="text-sm capitalize">{criterion.replace('_', ' ')}</span>
                        <div className="flex items-center gap-2">
                          <Progress value={score * 10} className="w-24" />
                          <span className={`text-sm font-medium ${getScoreColor(score)}`}>
                            {score.toFixed(1)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <div>
                    <h4 className="font-medium mb-2">Score Breakdown</h4>
                    <ResponsiveContainer width="100%" height={200}>
                      <BarChart data={Object.entries(data.scores).map(([k, v]) => ({ name: k, value: v }))}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis domain={[0, 10]} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#6366f1" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </CardContent>
      </Card>

      {/* Radar Chart Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Component Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="component" />
              <PolarRadiusAxis domain={[0, 10]} />
              <Radar name="Score" dataKey="score" stroke="#6366f1" fill="#6366f1" fillOpacity={0.6} />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Improvement Report */}
      {improvement_report && (
        <Card>
          <CardHeader>
            <CardTitle>Improvement Report</CardTitle>
            <CardDescription>{improvement_report.summary}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Strengths */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  Strengths
                </h4>
                <div className="space-y-2">
                  {improvement_report.strengths.map((strength, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-green-50 rounded">
                      <span className="text-sm">{strength.description}</span>
                      <Badge variant="outline" className="bg-green-100">
                        {strength.score.toFixed(1)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Priority Improvements */}
              <div>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-600" />
                  Priority Improvements
                </h4>
                <div className="space-y-2">
                  {improvement_report.priority_improvements.slice(0, 5).map((improvement, idx) => (
                    <div key={idx} className="p-2 bg-orange-50 rounded">
                      <div className="flex justify-between items-start mb-1">
                        <span className="text-sm font-medium">
                          {improvement.component} - {improvement.criterion}
                        </span>
                        <Badge variant="outline" className="bg-orange-100">
                          {improvement.score.toFixed(1)}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-600">{improvement.recommendation}</p>
                      {improvement.details && (
                        <p className="text-xs text-gray-500 mt-1">{improvement.details}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};