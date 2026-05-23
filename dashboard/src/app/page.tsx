import Link from 'next/link';
import { ArrowRight, Target, CheckCircle, Link2 } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            CrawlStory Dashboard
          </h1>
          <p className="text-xl text-gray-600">
            Automated Social Media Video Scraping & Discord Delivery
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto">
          <Link
            href="/dashboard/targets"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <Target className="w-12 h-12 text-blue-600" />
              <ArrowRight className="w-6 h-6 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Manage Targets
            </h2>
            <p className="text-gray-600">
              Add and manage social media profiles to scrape videos from
            </p>
          </Link>

          <Link
            href="/dashboard/mappings"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <Link2 className="w-12 h-12 text-purple-600" />
              <ArrowRight className="w-6 h-6 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Manage Mappings
            </h2>
            <p className="text-gray-600">
              View and edit Target → Channel mappings
            </p>
          </Link>

          <Link
            href="/dashboard/approval"
            className="bg-white rounded-lg shadow-lg p-8 hover:shadow-xl transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="w-12 h-12 text-green-600" />
              <ArrowRight className="w-6 h-6 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              AI Mapping Approval
            </h2>
            <p className="text-gray-600">
              Review and approve AI-suggested channel mappings
            </p>
          </Link>
        </div>
      </div>
    </div>
  );
}
