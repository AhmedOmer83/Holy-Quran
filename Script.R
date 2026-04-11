library(stylo)
# Define the path to the corpus directory
corpus_dir <- ""
# Load and parse the corpus
my.corpus <- load.corpus.and.parse(
  corpus.dir = corpus_dir,
  features = "w",
  ngram.size =1,
  analysis.type = "Cluster analysis",
  distance.measure = "delta",
  sample.size = 7000,
  number.of.samples = 10,
  sampling = "random.sampling",
  sample.overlap = 0,
  encoding = "UTF-8"
)
# Analyze the corpus with stylo
stylo_results <- stylo(parsed.corpus = my.corpus)
stylo_results$features.actually.used
