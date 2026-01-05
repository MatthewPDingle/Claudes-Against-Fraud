'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getFindings, type Finding } from '@/lib/api';
import { formatDistance } from 'date-fns';

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: '',
    category: '',
    jurisdiction: '',
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    const fetchFindings = async () => {
      try {
        setLoading(true);
        const data = await getFindings({
          ...filters,
          status: filters.status || undefined,
          category: filters.category || undefined,
          jurisdiction: filters.jurisdiction || undefined,
          page,
          per_page: 20,
        });
        setFindings(data.findings);
        setTotalPages(data.pages);
      } catch (err) {
        setError('Failed to load findings');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchFindings();
  }, [filters, page]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Public Findings</h1>
        <p className="text-gray-600">
          Browse verified findings of potential fraud in public spending
        </p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Filters</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="VERIFYING">Verifying</option>
              <option value="VERIFIED">Verified</option>
              <option value="PUBLISHED">Published</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category
            </label>
            <select
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">All Categories</option>
              <option value="procurement">Procurement</option>
              <option value="payroll">Payroll</option>
              <option value="grants">Grants</option>
              <option value="contracts">Contracts</option>
              <option value="infrastructure">Infrastructure</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Jurisdiction
            </label>
            <select
              value={filters.jurisdiction}
              onChange={(e) => setFilters({ ...filters, jurisdiction: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2"
            >
              <option value="">All Jurisdictions</option>
              <option value="federal">Federal</option>
              <option value="state:NY">New York</option>
              <option value="state:CA">California</option>
              <option value="state:TX">Texas</option>
            </select>
          </div>
        </div>
      </div>

      {/* Findings List */}
      {loading && (
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-lg">Loading findings...</div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {!loading && !error && findings.length === 0 && (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600">No findings match your filters</p>
        </div>
      )}

      {!loading && !error && findings.length > 0 && (
        <>
          <div className="space-y-4">
            {findings.map((finding) => (
              <FindingCard key={finding.finding_id} finding={finding} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Previous
              </button>
              <span className="px-4 py-2">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
                className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const statusColors = {
    PENDING: 'bg-yellow-100 text-yellow-800',
    VERIFYING: 'bg-blue-100 text-blue-800',
    VERIFIED: 'bg-green-100 text-green-800',
    PUBLISHED: 'bg-green-100 text-green-800',
    RETRACTED: 'bg-red-100 text-red-800',
    DISMISSED: 'bg-gray-100 text-gray-800',
  };

  return (
    <Link
      href={`/findings/${finding.finding_id}`}
      className="block bg-white rounded-lg shadow hover:shadow-lg transition-shadow p-6"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-xl font-semibold text-gray-900 flex-1 pr-4">
          {finding.title}
        </h3>
        <span className={`px-3 py-1 text-sm font-medium rounded-full ${statusColors[finding.status as keyof typeof statusColors] || 'bg-gray-100 text-gray-800'}`}>
          {finding.status}
        </span>
      </div>

      <p className="text-gray-600 mb-4 line-clamp-3">{finding.description}</p>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="bg-gray-100 px-3 py-1 rounded-full text-gray-700">
          {finding.category}
        </span>
        <span className="text-gray-500">{finding.jurisdiction}</span>
        {finding.estimated_amount && (
          <span className="font-semibold text-red-600">
            ${finding.estimated_amount.toLocaleString()}
          </span>
        )}
        {finding.confidence_score && (
          <span className="text-gray-500">
            {(parseFloat(finding.confidence_score.toString()) * 100).toFixed(0)}% confidence
          </span>
        )}
        <span className="ml-auto text-gray-500">
          {formatDistance(new Date(finding.created_at), new Date(), { addSuffix: true })}
        </span>
      </div>
    </Link>
  );
}
