import React from 'react';
import { Card } from '@/components/ui/card';
import { EnhancedDecisionCard } from './EnhancedDecisionCard';

// Demo component to showcase the enhanced decision cards
export const DecisionCardDemo = () => {
  const sampleDecisions = [
    {
      title: "Launch Date Change", 
      decision: "Push the launch date from October 15th to October 29th to allow for additional security testing and buffer time between development phases.",
      category: "timeline",
      participants: ["Sarah Chen", "Marcus Rodriguez", "Emily Davis"],
      supporting_statements: [
        "We need more buffer time between phases",
        "The security audit is taking longer than expected",
        "Let's move the launch two weeks later to be safe"
      ],
      quantitative_data: {
        dates: ["October 15th", "October 29th"],
        numbers: ["2", "14"],
        changes: ["October 15th → October 29th", "1 week → 2 weeks buffer"]
      },
      confidence: 0.95,
      decision_type: "explicit" as const,
      speaker: "Sarah Chen",
      timestamp: "14:23",
      provenance: {
        source_segment_ids: [42, 43, 44],
        source_text: [
          "We need to push the launch date back a bit",
          "I'm thinking October 29th gives us the buffer we need",
          "Everyone agreed with the new timeline"
        ],
        similarity_scores: [0.89, 0.92, 0.87],
        extraction_method: "llm"
      },
      validation: {
        is_valid: true,
        confidence: 0.95,
        source_support: 0.91,
        potential_hallucination: false
      }
    },
    {
      title: "Feature Set Finalization",
      decision: "Finalize the feature set to 10 core features and cut 4 nice-to-have features to meet the timeline and quality requirements.",
      category: "features",
      participants: ["Marcus Rodriguez", "Emily Davis"],
      supporting_statements: [
        "We can't do all 15 features with the current timeline",
        "Let's focus on the core 10 that provide the most value",
        "The 4 nice-to-haves can go into the next release"
      ],
      quantitative_data: {
        numbers: ["10", "4", "15"],
        changes: ["15 features → 10 core features", "4 nice-to-haves cut"]
      },
      confidence: 0.88,
      decision_type: "implicit" as const,
      speaker: "Marcus Rodriguez", 
      timestamp: "12:15", // Earlier timestamp to show sorting
      provenance: {
        source_segment_ids: [67, 68],
        source_text: [
          "We can't realistically do all 15 features",
          "Let's prioritize the 10 most important ones"
        ],
        similarity_scores: [0.82, 0.85],
        extraction_method: "llm"
      },
      validation: {
        is_valid: true,
        confidence: 0.88,
        source_support: 0.83,
        potential_hallucination: false
      }
    },
    {
      title: "Security Audit Budget Allocation", 
      decision: "Allocate $50K from the contingency budget to cover the external security audit costs, with Marcus handling the vendor selection process.",
      category: "budget",
      participants: ["Sarah Chen", "Marcus Rodriguez"],
      supporting_statements: [
        "We need to allocate budget for the security audit",
        "50K from contingency should cover the external assessment",
        "Marcus will handle getting quotes from vendors"
      ],
      quantitative_data: {
        numbers: ["50K", "$50,000"],
        changes: ["contingency → security audit allocation"]
      },
      confidence: 0.92,
      decision_type: "explicit" as const,
      speaker: "Sarah Chen",
      timestamp: "18:12",
      provenance: {
        source_segment_ids: [89, 90],
        source_text: [
          "Let's allocate 50K from contingency for the security audit",
          "Marcus can handle the vendor selection and quotes"
        ],
        similarity_scores: [0.94, 0.88],
        extraction_method: "llm"
      },
      validation: {
        is_valid: true,
        confidence: 0.92,
        source_support: 0.94,
        potential_hallucination: false
      }
    },
    {
      title: "General Process Update",
      decision: "Update the team on new policies and procedures for remote work collaboration.",
      category: "other", // This should not show a category badge
      participants: ["Emily Davis"],
      supporting_statements: [
        "Let's make sure everyone knows about the new policies",
        "Remote work guidelines have been updated"
      ],
      quantitative_data: {
        numbers: [],
        dates: [],
        changes: []
      },
      confidence: 0.98, // Higher confidence to show confidence sorting
      decision_type: "explicit" as const,
      speaker: "Emily Davis", 
      timestamp: "10:30", // Earliest timestamp
      provenance: {
        source_segment_ids: [95],
        source_text: [
          "Everyone should be aware of the new remote work policies"
        ],
        similarity_scores: [0.78],
        extraction_method: "llm"
      },
      validation: {
        is_valid: true,
        confidence: 0.75,
        source_support: 0.78,
        potential_hallucination: false
      }
    }
  ];

  const sampleSegments = [
    { text: "We need to push the launch date back a bit", speaker: "Sarah Chen", timestamp: "14:23" },
    { text: "I'm thinking October 29th gives us the buffer we need", speaker: "Sarah Chen", timestamp: "14:24" },
    { text: "Everyone agreed with the new timeline", speaker: "Emily Davis", timestamp: "14:25" },
    { text: "We can't realistically do all 15 features", speaker: "Marcus Rodriguez", timestamp: "16:45" },
    { text: "Let's prioritize the 10 most important ones", speaker: "Marcus Rodriguez", timestamp: "16:46" },
    { text: "Let's allocate 50K from contingency for the security audit", speaker: "Sarah Chen", timestamp: "18:12" },
    { text: "Marcus can handle the vendor selection and quotes", speaker: "Sarah Chen", timestamp: "18:13" }
  ];

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Enhanced Decision Cards - Demo</h2>
        <p className="text-muted-foreground mb-6">
          This demonstrates the streamlined Key Decisions UI with attribution, provenance context, 
          quantitative callouts, and confidence ordering.
        </p>
        
        <div className="space-y-6">
          <h3 className="text-lg font-semibold">Features Showcased:</h3>
          <ul className="list-disc list-inside space-y-2 text-sm text-muted-foreground">
            <li>🎯 <strong>Confidence ordering</strong> - Highest-confidence decisions surface first</li>
            <li>🏷️ <strong>Category-based color coding</strong> - Visual distinction for timeline, features, budget, etc. (hides "other")</li>
            <li>👤 <strong>Attribution tracking</strong> - Shows who made the decision and when</li>
            <li>🔍 <strong>Confidence indicators</strong> - Shows explicit vs implicit decisions</li>
            <li>📝 <strong>Supporting context</strong> - Inline rationale snippets without extra clicks</li>
            <li>🔗 <strong>Source traceability</strong> - Key source excerpts surfaced alongside each decision</li>
            <li>🧹 <strong>Clean interface</strong> - Single-card layout keeps all decisions together</li>
          </ul>
        </div>
      </Card>

      <div className="space-y-4">
        {sampleDecisions.map((decision, idx) => (
          <EnhancedDecisionCard
            key={idx}
            decision={decision}
            originalSegments={sampleSegments}
            index={idx}
            displayNumber={idx + 1}
          />
        ))}
      </div>

      <Card className="p-6 bg-blue-50/50 dark:bg-blue-950/20 border-blue-200/50">
        <h3 className="text-lg font-semibold mb-4 text-blue-800 dark:text-blue-300">
          🎯 User Experience Improvements
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h4 className="font-medium mb-2">Visual Enhancements:</h4>
            <ul className="space-y-1 text-muted-foreground">
              <li>• Color-coded categories for quick scanning</li>
              <li>• Clear visual hierarchy with proper spacing</li>
              <li>• Hover effects and smooth transitions</li>
              <li>• Confidence badges with contextual information</li>
            </ul>
          </div>
          <div>
            <h4 className="font-medium mb-2">Functional Improvements:</h4>
            <ul className="space-y-1 text-muted-foreground">
              <li>• Confidence-first ordering to highlight critical decisions</li>
              <li>• Attribution bar for accountability</li>
              <li>• Source traceability for verification</li>
              <li>• Inline supporting statements for quick validation</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};