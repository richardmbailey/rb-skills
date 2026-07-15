#!/usr/bin/env ruby
# frozen_string_literal: true

require "yaml"

repo = File.expand_path(ARGV[0] || File.join(__dir__, "..", ".."))
errors = []
word_counts = {}

Dir.glob(File.join(repo, "rb-*", "SKILL.md")).sort.each do |skill_file|
  skill_dir = File.basename(File.dirname(skill_file))
  text = File.read(skill_file, encoding: "UTF-8")
  match = text.match(/\A---\s*\n(.*?)\n---\s*\n/m)
  unless match
    errors << "#{skill_file}: missing or malformed YAML frontmatter"
    next
  end

  begin
    metadata = YAML.safe_load(match[1], permitted_classes: [], aliases: false)
  rescue Psych::SyntaxError => e
    errors << "#{skill_file}: invalid YAML: #{e.message.lines.first.strip}"
    next
  end

  unless metadata.is_a?(Hash)
    errors << "#{skill_file}: frontmatter must be a mapping"
    next
  end

  name = metadata["name"]
  description = metadata["description"]
  errors << "#{skill_file}: name must equal directory #{skill_dir}" unless name == skill_dir
  unless description.is_a?(String) && !description.strip.empty?
    errors << "#{skill_file}: description must be a non-empty string"
    next
  end
  errors << "#{skill_file}: description exceeds 1024 characters" if description.length > 1024
  word_counts[skill_dir] = description.split.length unless skill_dir == "rb-wiki"

  agent_file = File.join(File.dirname(skill_file), "agents", "openai.yaml")
  unless File.file?(agent_file)
    errors << "#{agent_file}: missing"
    next
  end

  begin
    agent = YAML.safe_load(
      File.read(agent_file, encoding: "UTF-8"),
      permitted_classes: [],
      aliases: false
    )
  rescue Psych::SyntaxError => e
    errors << "#{agent_file}: invalid YAML: #{e.message.lines.first.strip}"
    next
  end
  interface = agent.is_a?(Hash) ? agent["interface"] : nil
  unless interface.is_a?(Hash)
    errors << "#{agent_file}: interface must be a mapping"
    next
  end

  %w[display_name short_description default_prompt].each do |field|
    value = interface[field]
    errors << "#{agent_file}: #{field} must be a non-empty string" unless value.is_a?(String) && !value.strip.empty?
  end
  short = interface["short_description"]
  if short.is_a?(String) && !(25..64).cover?(short.length)
    errors << "#{agent_file}: short_description must contain 25 to 64 characters"
  end
  prompt = interface["default_prompt"]
  if prompt.is_a?(String) && !prompt.include?("$#{skill_dir}")
    errors << "#{agent_file}: default_prompt must mention $#{skill_dir}"
  end
end

total_words = word_counts.values.sum
over_40 = word_counts.select { |_name, count| count > 40 }
errors << "in-scope description words #{total_words} exceed the 975-word budget" if total_words > 975
errors << "#{over_40.length} descriptions exceed 40 words; expected fewer than 8" if over_40.length >= 8

if errors.empty?
  puts "PASS: #{word_counts.length} in-scope skills, #{total_words} description words, #{over_40.length} descriptions over 40 words"
  exit 0
end

warn "FAIL: skill metadata"
errors.each { |error| warn "- #{error}" }
exit 1
