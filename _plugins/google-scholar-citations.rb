require "active_support/all"

module Helpers
  extend ActiveSupport::NumberHelper
end

module Jekyll
  # Citation counts are updated separately and stored in _data/scholar_citations.yml.
  # Never fetch Google Scholar during a Jekyll build: temporary rate limits must
  # not replace previously verified counts with "N/A".
  class GoogleScholarCitationsTag < Liquid::Tag
    def initialize(tag_name, params, tokens)
      super
      @scholar_id, @article_id = params.split.map(&:strip)
    end

    def render(context)
      return "View" if @article_id.nil? || @scholar_id.nil?

      article_id = context[@article_id].to_s
      counts = context.registers[:site].data.fetch("scholar_citations", {})
      count = counts[article_id]
      return "View" unless count.is_a?(Integer) && count >= 0

      Helpers.number_to_human(count, format: "%n%u", precision: 2, units: { thousand: "K", million: "M", billion: "B" })
    end
  end
end

Liquid::Template.register_tag("google_scholar_citations", Jekyll::GoogleScholarCitationsTag)
