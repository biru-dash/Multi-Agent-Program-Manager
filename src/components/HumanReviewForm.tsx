import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { CheckCircle, AlertCircle, Save } from 'lucide-react';

interface HumanReviewFormProps {
  jobId: string;
  extractionResults: any;
  onReviewSubmitted?: () => void;
}

interface ComponentReview {
  scores: { [key: string]: number };
  explanations: { [key: string]: string };
}

interface EvaluationSchema {
  components: {
    [key: string]: {
      criteria: string[];
      descriptions: { [key: string]: string };
    };
  };
}

export const HumanReviewForm: React.FC<HumanReviewFormProps> = ({ 
  jobId, 
  extractionResults,
  onReviewSubmitted 
}) => {
  const [schema, setSchema] = useState<EvaluationSchema | null>(null);
  const [reviews, setReviews] = useState<{ [key: string]: ComponentReview }>({});
  const [overallFeedback, setOverallFeedback] = useState<{ [key: string]: string }>({});
  const [markForRetraining, setMarkForRetraining] = useState<{ [key: string]: boolean }>({});
  const [submittedComponents, setSubmittedComponents] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    fetchSchema();
  }, []);

  const fetchSchema = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/evaluation/schema');
      if (!response.ok) throw new Error('Failed to fetch schema');
      const data = await response.json();
      setSchema(data);
      
      // Initialize review state
      const initialReviews: { [key: string]: ComponentReview } = {};
      Object.keys(data.components).forEach(component => {
        initialReviews[component] = {
          scores: {},
          explanations: {}
        };
        data.components[component].criteria.forEach((criterion: string) => {
          initialReviews[component].scores[criterion] = 5;
          initialReviews[component].explanations[criterion] = '';
        });
      });
      setReviews(initialReviews);
    } catch (err) {
      setError('Failed to load evaluation schema');
    }
  };

  const updateScore = (component: string, criterion: string, value: number) => {
    setReviews(prev => ({
      ...prev,
      [component]: {
        ...prev[component],
        scores: {
          ...prev[component].scores,
          [criterion]: value
        }
      }
    }));
  };

  const updateExplanation = (component: string, criterion: string, value: string) => {
    setReviews(prev => ({
      ...prev,
      [component]: {
        ...prev[component],
        explanations: {
          ...prev[component].explanations,
          [criterion]: value
        }
      }
    }));
  };

  const submitReview = async (component: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await fetch(`http://localhost:8000/api/evaluation/${jobId}/human-review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          component,
          scores: reviews[component].scores,
          explanations: reviews[component].explanations,
          overall_feedback: overallFeedback[component] || null,
          mark_for_retraining: markForRetraining[component] || false
        })
      });

      if (!response.ok) throw new Error('Failed to submit review');
      
      setSubmittedComponents(prev => new Set([...prev, component]));
      setSuccess(`Review for ${component} submitted successfully!`);
      
      if (onReviewSubmitted) {
        onReviewSubmitted();
      }
    } catch (err) {
      setError('Failed to submit review');
    } finally {
      setLoading(false);
    }
  };

  const getScoreLabel = (score: number): string => {
    if (score >= 9) return 'Excellent';
    if (score >= 7) return 'Good';
    if (score >= 5) return 'Average';
    if (score >= 3) return 'Below Average';
    return 'Poor';
  };

  const getScoreColor = (score: number): string => {
    if (score >= 7) return 'text-green-600';
    if (score >= 5) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (!schema) {
    return <div>Loading...</div>;
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Human Review</CardTitle>
        <CardDescription>
          Evaluate the extraction quality for each component
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error && (
          <Alert className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        
        {success && (
          <Alert className="mb-4 border-green-200 bg-green-50">
            <CheckCircle className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">{success}</AlertDescription>
          </Alert>
        )}

        <Tabs defaultValue="summary">
          <TabsList className="grid grid-cols-4 w-full">
            {Object.keys(schema.components).map((component) => (
              <TabsTrigger key={component} value={component}>
                <span className="flex items-center gap-2">
                  {component.charAt(0).toUpperCase() + component.slice(1).replace('_', ' ')}
                  {submittedComponents.has(component) && (
                    <CheckCircle className="h-3 w-3 text-green-600" />
                  )}
                </span>
              </TabsTrigger>
            ))}
          </TabsList>

          {Object.entries(schema.components).map(([component, config]) => (
            <TabsContent key={component} value={component} className="space-y-6">
              {/* Display extracted content */}
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium mb-2">Extracted Content</h4>
                <div className="max-h-48 overflow-y-auto">
                  {component === 'summary' ? (
                    <p className="text-sm">{extractionResults?.[component]}</p>
                  ) : (
                    <ul className="text-sm space-y-1">
                      {extractionResults?.[component]?.map((item: any, idx: number) => (
                        <li key={idx}>
                          • {typeof item === 'string' ? item : JSON.stringify(item, null, 2)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>

              {/* Criteria evaluation */}
              <div className="space-y-4">
                {config.criteria.map((criterion) => (
                  <div key={criterion} className="space-y-2">
                    <div className="flex justify-between items-start">
                      <div>
                        <Label className="text-sm font-medium capitalize">
                          {criterion.replace('_', ' ')}
                        </Label>
                        <p className="text-xs text-gray-500">
                          {config.descriptions[criterion]}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`text-sm font-medium ${getScoreColor(reviews[component]?.scores[criterion] || 5)}`}>
                          {reviews[component]?.scores[criterion] || 5}/10
                        </span>
                        <Badge variant="outline" className={getScoreColor(reviews[component]?.scores[criterion] || 5)}>
                          {getScoreLabel(reviews[component]?.scores[criterion] || 5)}
                        </Badge>
                      </div>
                    </div>
                    
                    <Slider
                      value={[reviews[component]?.scores[criterion] || 5]}
                      onValueChange={([value]) => updateScore(component, criterion, value)}
                      max={10}
                      min={0}
                      step={1}
                      className="w-full"
                    />
                    
                    <Textarea
                      placeholder="Explain your rating (optional)..."
                      value={reviews[component]?.explanations[criterion] || ''}
                      onChange={(e) => updateExplanation(component, criterion, e.target.value)}
                      className="h-20 resize-none text-sm"
                    />
                  </div>
                ))}
              </div>

              {/* Overall feedback */}
              <div className="space-y-2">
                <Label>Overall Feedback (Optional)</Label>
                <Textarea
                  placeholder="Any additional comments about this component..."
                  value={overallFeedback[component] || ''}
                  onChange={(e) => setOverallFeedback(prev => ({ ...prev, [component]: e.target.value }))}
                  className="h-24"
                />
              </div>

              {/* Mark for retraining */}
              <div className="flex items-center space-x-2">
                <Checkbox
                  id={`retrain-${component}`}
                  checked={markForRetraining[component] || false}
                  onCheckedChange={(checked) => 
                    setMarkForRetraining(prev => ({ ...prev, [component]: checked as boolean }))
                  }
                />
                <Label htmlFor={`retrain-${component}`} className="text-sm cursor-pointer">
                  Mark this extraction for retraining (poor quality example)
                </Label>
              </div>

              {/* Submit button */}
              <Button
                onClick={() => submitReview(component)}
                disabled={loading}
                className="w-full"
              >
                <Save className="h-4 w-4 mr-2" />
                {submittedComponents.has(component) ? 'Update Review' : 'Submit Review'}
              </Button>
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
};